"""Thin production workflow service behind the AutoVD MCP tools."""

import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from mcp.types import CallToolResult, ResourceLink, TextContent
from pydantic import BaseModel, ConfigDict, Field

from autovd.contracts.edit_plan import CutCandidate, EditPlanLimits, validate_cut_candidates
from autovd.contracts.openai_files import OpenAIFile
from autovd.jobs.store import JobStore, JobStoreError, PreparedJob
from autovd.media.download import FileDownloadError, download_openai_files
from autovd.media.frame_sampler import FramePayloadLimitError
from autovd.media.ingest import IngestedClip, MediaIngestError, MediaLimits
from autovd.media.motion import (
    MotionAnalysisError,
    MotionConfig,
    detect_low_motion_regions,
    measure_motion_scores,
)
from autovd.media.renderer import (
    ClipRenderPlan,
    MusicTrack,
    RendererError,
    RenderProfile,
)
from autovd.media.renderer import render_video as render_core_video
from autovd.media.timeline import build_render_segments
from autovd.tools.analysis_spike import build_temporal_evidence

_MUSIC_SUFFIXES = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}


class DownloadFiles(Protocol):
    def __call__(
        self,
        files: list[OpenAIFile],
        *,
        destination_dir: Path,
        max_file_bytes: int,
        timeout_seconds: float,
    ) -> list[Path]: ...


class ClipEditRequest(BaseModel):
    """Model-provided candidate decisions for one clip."""

    model_config = ConfigDict(extra="forbid")

    clip_id: str = Field(min_length=1)
    candidates: list[CutCandidate] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    """Server-owned operational knobs for the MVP workflow."""

    media_limits: MediaLimits
    motion: MotionConfig
    edit_limits: EditPlanLimits
    render_profile: RenderProfile
    download_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.download_timeout_seconds <= 0:
            raise ValueError("download_timeout_seconds must be positive")


class WorkflowService:
    """Coordinate validated deterministic core operations across MCP calls."""

    def __init__(
        self,
        *,
        store: JobStore,
        config: WorkflowConfig,
        music_dir: Path,
        downloader: DownloadFiles = download_openai_files,
        rng: random.Random | None = None,
    ) -> None:
        self.store = store
        self.config = config
        self.music_dir = music_dir
        self.downloader = downloader
        self.rng = rng or random.SystemRandom()

    def prepare_video_analysis(self, videos: list[OpenAIFile]) -> dict[str, object]:
        """Download, validate, and stage ChatGPT-uploaded clips in trusted order."""
        if not videos or len(videos) > self.config.media_limits.max_clips:
            return {"status": "error", "error": "clip count exceeds configured limit"}

        try:
            with TemporaryDirectory(prefix="autovd-download-") as staging_dir:
                staged = self.downloader(
                    videos,
                    destination_dir=Path(staging_dir),
                    max_file_bytes=self.config.media_limits.max_file_bytes,
                    timeout_seconds=self.config.download_timeout_seconds,
                )
                job = self.store.create_from_staged(staged, limits=self.config.media_limits)
        except (FileDownloadError, MediaIngestError, JobStoreError):
            return {"status": "error", "error": "uploaded video could not be prepared"}

        return {
            "status": "prepared",
            "job_id": job.job_id,
            "clips": [
                {
                    "clip_id": clip.clip_id,
                    "order": clip.order,
                    "duration_ms": clip.duration_ms,
                    "width": clip.width,
                    "height": clip.height,
                    "codec_name": clip.codec_name,
                }
                for clip in job.clips
            ],
        }

    def get_analysis_chunk(
        self,
        *,
        job_id: str,
        clip_id: str,
        start_ms: int = 0,
        end_ms: int | None = None,
        interval_ms: int = 500,
        max_frames: int = 8,
    ) -> CallToolResult:
        """Return bounded timestamp/image evidence for one prepared clip interval."""
        try:
            job = self.store.get(job_id)
            clip = self._find_clip(job, clip_id)
            resolved_end = clip.duration_ms if end_ms is None else end_ms
            if start_ms < 0 or start_ms >= resolved_end or resolved_end > clip.duration_ms:
                raise ValueError("analysis range is invalid")
            return build_temporal_evidence(
                clip.path,
                clip_id=clip.clip_id,
                interval_ms=interval_ms,
                max_frames=max_frames,
                start_ms=start_ms,
                end_ms=resolved_end,
            )
        except (
            JobStoreError,
            ValueError,
            FileNotFoundError,
            FramePayloadLimitError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ):
            return CallToolResult(
                content=[
                    TextContent(type="text", text="Analysis chunk is unavailable or invalid.")
                ],
                is_error=True,
            )

    def render_video(self, *, job_id: str, edits: list[ClipEditRequest]) -> CallToolResult:
        """Validate model edits, compute pacing, render, and return an MCP resource link."""
        try:
            job = self.store.get(job_id)
            edit_by_clip: dict[str, ClipEditRequest] = {}
            for edit in edits:
                if edit.clip_id in edit_by_clip:
                    raise ValueError("duplicate clip edit")
                edit_by_clip[edit.clip_id] = edit
            known_ids = {clip.clip_id for clip in job.clips}
            if not set(edit_by_clip).issubset(known_ids):
                raise ValueError("unknown clip edit")

            plans: list[ClipRenderPlan] = []
            for clip in job.clips:
                edit = edit_by_clip.get(clip.clip_id)
                cuts = validate_cut_candidates(
                    edit.candidates if edit is not None else [],
                    clip_id=clip.clip_id,
                    clip_duration_ms=clip.duration_ms,
                    limits=self.config.edit_limits,
                )
                scores = measure_motion_scores(clip.path, self.config.motion)
                speed_regions = detect_low_motion_regions(
                    scores,
                    clip_duration_ms=clip.duration_ms,
                    config=self.config.motion,
                )
                segments = build_render_segments(
                    clip_duration_ms=clip.duration_ms,
                    cuts=cuts,
                    speed_regions=speed_regions,
                )
                plans.append(ClipRenderPlan(clip=clip, segments=tuple(segments)))

            music_tracks = self._music_tracks()
            output_path = job.workspace.path / "output.mp4"
            rendered = render_core_video(
                plans,
                music_tracks=music_tracks,
                output_path=output_path,
                profile=self.config.render_profile,
                rng=self.rng,
            )
            self.store.set_output(job.job_id, output_path)
            resource_uri = f"autovd://jobs/{job.job_id}/output"
            return CallToolResult(
                content=[
                    TextContent(type="text", text="AutoVD render completed."),
                    ResourceLink(
                        type="resource_link",
                        name="AutoVD rendered video",
                        uri=resource_uri,
                        mime_type="video/mp4",
                    ),
                ],
                structured_content={
                    "status": "completed",
                    "job_id": job.job_id,
                    "music_track_id": rendered.music_track_id,
                    "expected_duration_ms": rendered.expected_duration_ms,
                    "output_resource_uri": resource_uri,
                },
                is_error=False,
            )
        except (
            JobStoreError,
            ValueError,
            MotionAnalysisError,
            RendererError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ):
            return CallToolResult(
                content=[TextContent(type="text", text="Video render could not be completed.")],
                is_error=True,
            )

    def read_rendered_output(self, job_id: str) -> bytes:
        """Read one completed output for the MCP output resource."""
        try:
            return self.store.read_output(job_id)
        except JobStoreError as exc:
            raise ValueError("rendered output is unavailable") from exc

    @staticmethod
    def _find_clip(job: PreparedJob, clip_id: str) -> IngestedClip:
        for clip in job.clips:
            if clip.clip_id == clip_id:
                return clip
        raise ValueError("unknown clip")

    def _music_tracks(self) -> list[MusicTrack]:
        if not self.music_dir.is_dir():
            raise RendererError("music library is unavailable")
        tracks = [
            MusicTrack(track_id=path.stem, path=path)
            for path in sorted(self.music_dir.iterdir())
            if path.is_file() and not path.is_symlink() and path.suffix.lower() in _MUSIC_SUFFIXES
        ]
        if not tracks:
            raise RendererError("music library is empty")
        return tracks
