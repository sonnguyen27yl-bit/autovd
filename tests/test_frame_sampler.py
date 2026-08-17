from pathlib import Path
import subprocess

import pytest

from autovd.media.frame_sampler import sample_video_frames


def _make_video(path: Path) -> None:
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
            "color=c=red:s=64x64:r=10:d=2",
            "-an",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_sample_video_frames_returns_ordered_timestamped_pngs(tmp_path: Path) -> None:
    video_path = tmp_path / "fixture.mp4"
    _make_video(video_path)

    frames = sample_video_frames(video_path, interval_ms=500, max_frames=8)

    assert [frame.timestamp_ms for frame in frames] == [0, 500, 1000, 1500]
    assert all(frame.png_bytes.startswith(b"\x89PNG\r\n\x1a\n") for frame in frames)


def test_sample_video_frames_rejects_invalid_interval(tmp_path: Path) -> None:
    video_path = tmp_path / "fixture.mp4"
    _make_video(video_path)

    with pytest.raises(ValueError, match="interval_ms"):
        sample_video_frames(video_path, interval_ms=0)
