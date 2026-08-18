import subprocess
from pathlib import Path

import pytest

from autovd.jobs.workspace import JobWorkspace
from autovd.media.ingest import MediaIngestError, MediaLimits, ingest_staged_media


def _make_video(path: Path, *, duration_seconds: float = 1.0) -> None:
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
            f"testsrc2=s=64x64:r=10:d={duration_seconds}",
            "-an",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _limits(*, max_clips: int = 4, max_bytes: int = 10_000_000, max_duration_ms: int = 5_000) -> MediaLimits:
    return MediaLimits(
        max_clips=max_clips,
        max_file_bytes=max_bytes,
        max_duration_ms=max_duration_ms,
    )


def test_ingest_preserves_order_and_uses_internal_paths(tmp_path: Path) -> None:
    first = tmp_path / "first-user-name.mp4"
    second = tmp_path / "second-user-name.mp4"
    _make_video(first)
    _make_video(second)

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        clips = ingest_staged_media([first, second], workspace=workspace, limits=_limits())

        assert [clip.order for clip in clips] == [0, 1]
        assert [clip.clip_id for clip in clips] == ["clip_0000", "clip_0001"]
        assert [clip.duration_ms for clip in clips] == [1000, 1000]
        assert all(clip.path.parent == workspace.path for clip in clips)
        assert all(clip.path.exists() for clip in clips)
        assert first.name not in {clip.path.name for clip in clips}
        assert second.name not in {clip.path.name for clip in clips}


def test_workspace_is_deleted_on_context_exit(tmp_path: Path) -> None:
    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        workspace_path = workspace.path
        assert workspace_path.is_dir()

    assert not workspace_path.exists()


def test_ingest_rejects_invalid_media(tmp_path: Path) -> None:
    invalid = tmp_path / "not-video.bin"
    invalid.write_bytes(b"not a video")

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        with pytest.raises(MediaIngestError, match="valid video"):
            ingest_staged_media([invalid], workspace=workspace, limits=_limits())


def test_ingest_rejects_count_limit(tmp_path: Path) -> None:
    first = tmp_path / "one.mp4"
    second = tmp_path / "two.mp4"
    _make_video(first)
    _make_video(second)

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        with pytest.raises(MediaIngestError, match="clip count"):
            ingest_staged_media([first, second], workspace=workspace, limits=_limits(max_clips=1))


def test_ingest_rejects_size_limit(tmp_path: Path) -> None:
    video = tmp_path / "fixture.mp4"
    _make_video(video)

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        with pytest.raises(MediaIngestError, match="file size"):
            ingest_staged_media([video], workspace=workspace, limits=_limits(max_bytes=1))


def test_ingest_rejects_duration_limit(tmp_path: Path) -> None:
    video = tmp_path / "fixture.mp4"
    _make_video(video, duration_seconds=2.0)

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        with pytest.raises(MediaIngestError, match="duration"):
            ingest_staged_media([video], workspace=workspace, limits=_limits(max_duration_ms=500))


def test_media_limits_reject_non_positive_values() -> None:
    with pytest.raises(ValueError, match="max_clips"):
        MediaLimits(max_clips=0, max_file_bytes=10, max_duration_ms=10)
