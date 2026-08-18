"""Deterministic FFmpeg renderer for the AutoVD MVP vertical slice."""

import random
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from autovd.media.ingest import IngestedClip
from autovd.media.probe import MediaProbeError, probe_video
from autovd.media.timeline import RenderSegment


class RendererError(ValueError):
    """Raised when a validated render plan cannot be rendered safely."""


@dataclass(frozen=True, slots=True)
class RenderProfile:
    """Canonical output shape for one deterministic render."""

    width: int
    height: int
    fps: int
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("render dimensions must be positive")
        if self.width % 2 or self.height % 2:
            raise ValueError("render dimensions must be even for yuv420p")
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class MusicTrack:
    """One server-curated music track eligible for output audio."""

    track_id: str
    path: Path

    def __post_init__(self) -> None:
        if not self.track_id:
            raise ValueError("music track_id must not be empty")


@dataclass(frozen=True, slots=True)
class ClipRenderPlan:
    """One ingested clip plus its retained timeline segments."""

    clip: IngestedClip
    segments: tuple[RenderSegment, ...]


@dataclass(frozen=True, slots=True)
class BuiltRenderCommand:
    """Validated FFmpeg invocation plus deterministic render metadata."""

    command: list[str]
    filter_complex: str
    music_track: MusicTrack
    music_input_index: int
    expected_duration_ms: int


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Verified output metadata returned by the renderer core."""

    output_path: Path
    music_track_id: str
    expected_duration_ms: int


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


def _validate_plan(plan: ClipRenderPlan) -> None:
    clip = plan.clip
    if clip.path.is_symlink() or not clip.path.is_file():
        raise RendererError("render source is unavailable")

    previous_end: int | None = None
    for segment in plan.segments:
        if segment.end_ms > clip.duration_ms:
            raise RendererError("render segment exceeds clip duration")
        if previous_end is not None and segment.start_ms < previous_end:
            raise RendererError("render segments must not overlap or move backwards")
        previous_end = segment.end_ms


def _validate_output_path(output_path: Path, source_paths: set[Path]) -> None:
    if output_path.suffix.lower() != ".mp4":
        raise RendererError("output must use the .mp4 container")
    if output_path.is_symlink():
        raise RendererError("output path must not be a symlink")
    if not output_path.parent.is_dir():
        raise RendererError("output directory is unavailable")
    if output_path in source_paths:
        raise RendererError("output path must not overwrite an input")


def _choose_music_track(
    music_tracks: Sequence[MusicTrack],
    *,
    rng: random.Random,
    source_paths: set[Path],
) -> MusicTrack:
    if not music_tracks:
        raise RendererError("music library is empty")

    chosen = rng.choice(list(music_tracks))
    if chosen.path.is_symlink() or not chosen.path.is_file():
        raise RendererError("selected music track is unavailable")
    if chosen.path in source_paths:
        raise RendererError("music track must be separate from source video")
    return chosen


def build_render_command(
    plans: Sequence[ClipRenderPlan],
    *,
    music_tracks: Sequence[MusicTrack],
    output_path: Path,
    profile: RenderProfile,
    rng: random.Random,
) -> BuiltRenderCommand:
    """Build one argv-only FFmpeg render command from trusted core objects."""
    if not plans:
        raise RendererError("render plan is empty")

    ordered_plans = sorted(plans, key=lambda plan: plan.clip.order)
    if len({plan.clip.order for plan in ordered_plans}) != len(ordered_plans):
        raise RendererError("clip order values must be unique")

    active_plans: list[ClipRenderPlan] = []
    for plan in ordered_plans:
        _validate_plan(plan)
        if plan.segments:
            active_plans.append(plan)
    if not active_plans:
        raise RendererError("no retained video content to render")

    source_paths = {plan.clip.path for plan in ordered_plans}
    _validate_output_path(output_path, source_paths)
    music_track = _choose_music_track(music_tracks, rng=rng, source_paths=source_paths)

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for plan in active_plans:
        command.extend(["-i", str(plan.clip.path)])

    music_input_index = len(active_plans)
    command.extend(["-stream_loop", "-1", "-i", str(music_track.path)])

    filters: list[str] = []
    video_labels: list[str] = []
    expected_duration = 0.0
    segment_index = 0
    for input_index, plan in enumerate(active_plans):
        for segment in plan.segments:
            output_label = f"v{segment_index}"
            filters.append(
                f"[{input_index}:v:0]"
                f"trim=start={_seconds(segment.start_ms)}:end={_seconds(segment.end_ms)},"
                f"setpts=(PTS-STARTPTS)/{segment.speed_factor:.6f},"
                f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,"
                f"pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2,"
                f"fps={profile.fps},setsar=1[{output_label}]"
            )
            video_labels.append(f"[{output_label}]")
            expected_duration += (segment.end_ms - segment.start_ms) / segment.speed_factor
            segment_index += 1

    filters.append(f"{''.join(video_labels)}concat=n={len(video_labels)}:v=1:a=0[vout]")
    filter_complex = ";".join(filters)
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            f"{music_input_index}:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    return BuiltRenderCommand(
        command=command,
        filter_complex=filter_complex,
        music_track=music_track,
        music_input_index=music_input_index,
        expected_duration_ms=round(expected_duration),
    )


def render_video(
    plans: Sequence[ClipRenderPlan],
    *,
    music_tracks: Sequence[MusicTrack],
    output_path: Path,
    profile: RenderProfile,
    rng: random.Random,
) -> RenderResult:
    """Render and probe one H.264/AAC MP4 using only validated argv inputs."""
    built = build_render_command(
        plans,
        music_tracks=music_tracks,
        output_path=output_path,
        profile=profile,
        rng=rng,
    )
    try:
        subprocess.run(
            built.command,
            check=True,
            capture_output=True,
            timeout=profile.timeout_seconds,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RendererError("video render failed") from exc

    try:
        rendered = probe_video(output_path)
    except MediaProbeError as exc:
        raise RendererError("rendered output is invalid") from exc
    if rendered.codec_name != "h264":
        raise RendererError("rendered output video codec is invalid")

    return RenderResult(
        output_path=output_path,
        music_track_id=built.music_track.track_id,
        expected_duration_ms=built.expected_duration_ms,
    )
