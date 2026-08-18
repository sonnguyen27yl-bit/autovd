import random
import shutil
import subprocess
from pathlib import Path

from mcp.types import ImageContent, ResourceLink

from autovd.contracts.edit_plan import EditPlanLimits
from autovd.contracts.openai_files import OpenAIFile
from autovd.jobs.store import JobStore
from autovd.media.ingest import MediaLimits
from autovd.media.motion import MotionConfig
from autovd.media.renderer import RenderProfile
from autovd.tools.workflow import WorkflowConfig, WorkflowService


def _make_video(path: Path, *, duration_seconds: float = 1.5) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=s=96x64:r=10:d={duration_seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration_seconds}",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _make_music(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=0.5",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _service(tmp_path: Path, source_paths: list[Path]) -> WorkflowService:
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    _make_music(music_dir / "track-1.m4a")

    def fake_downloader(
        files: list[OpenAIFile],
        *,
        destination_dir: Path,
        max_file_bytes: int,
        timeout_seconds: float,
    ) -> list[Path]:
        assert len(files) == len(source_paths)
        assert max_file_bytes > 0
        assert timeout_seconds > 0
        staged: list[Path] = []
        for index, source in enumerate(source_paths):
            target = destination_dir / f"staged_{index}.media"
            shutil.copyfile(source, target)
            staged.append(target)
        return staged

    return WorkflowService(
        store=JobStore(root=tmp_path / "jobs", max_jobs=4),
        config=WorkflowConfig(
            media_limits=MediaLimits(
                max_clips=4,
                max_file_bytes=5_000_000,
                max_duration_ms=5_000,
            ),
            motion=MotionConfig(
                frame_interval_ms=500,
                threshold=0.0,
                min_low_motion_ms=1_000,
                speed_factor=2.0,
                max_frames=16,
            ),
            edit_limits=EditPlanLimits(max_cut_intervals=8),
            render_profile=RenderProfile(width=96, height=64, fps=10),
        ),
        music_dir=music_dir,
        downloader=fake_downloader,
        rng=random.Random(1),
    )


def test_workflow_prepares_analyzes_renders_and_reads_output(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    _make_video(first)
    _make_video(second, duration_seconds=1.0)
    service = _service(tmp_path, [first, second])

    prepared = service.prepare_video_analysis(
        [
            OpenAIFile(download_url="https://files.example/one", file_id="file_1"),
            OpenAIFile(download_url="https://files.example/two", file_id="file_2"),
        ]
    )

    assert prepared["status"] == "prepared"
    job_id = prepared["job_id"]
    assert isinstance(job_id, str)
    clips = prepared["clips"]
    assert isinstance(clips, list)
    assert [clip["clip_id"] for clip in clips] == ["clip_0000", "clip_0001"]

    chunk = service.get_analysis_chunk(
        job_id=job_id,
        clip_id="clip_0000",
        start_ms=500,
        end_ms=1500,
        interval_ms=500,
        max_frames=4,
    )
    assert chunk.is_error is False
    assert chunk.structured_content is not None
    assert chunk.structured_content["timestamps_ms"] == [500, 1000]
    assert sum(isinstance(block, ImageContent) for block in chunk.content) == 2

    rendered = service.render_video(job_id=job_id, edits=[])
    assert rendered.is_error is False
    assert rendered.structured_content is not None
    assert rendered.structured_content["status"] == "completed"
    assert rendered.structured_content["music_track_id"] == "track-1"
    resource_links = [block for block in rendered.content if isinstance(block, ResourceLink)]
    assert len(resource_links) == 1
    assert str(resource_links[0].uri) == f"autovd://jobs/{job_id}/output"
    assert resource_links[0].mime_type == "video/mp4"

    output_bytes = service.read_rendered_output(job_id)
    assert len(output_bytes) > 100
    assert b"ftyp" in output_bytes[:32]


def test_workflow_returns_safe_error_for_unknown_job(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    _make_video(source)
    service = _service(tmp_path, [source])

    chunk = service.get_analysis_chunk(job_id="does-not-exist", clip_id="clip_0000")
    rendered = service.render_video(job_id="does-not-exist", edits=[])

    assert chunk.is_error is True
    assert rendered.is_error is True
    assert "does-not-exist" not in str(chunk.content)
    assert "does-not-exist" not in str(rendered.content)
