import subprocess
from pathlib import Path

import pytest

from autovd.media import frame_sampler
from autovd.media.frame_sampler import FramePayloadLimitError, sample_video_frames


def _make_video(
    path: Path,
    *,
    size: str = "64x64",
    duration_seconds: float = 2,
) -> None:
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
            f"testsrc2=s={size}:r=10:d={duration_seconds}",
            "-an",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    return (
        int.from_bytes(png_bytes[16:20], "big"),
        int.from_bytes(png_bytes[20:24], "big"),
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


def test_sample_video_frames_downscales_large_input_and_bounds_total_payload(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "large-fixture.mp4"
    _make_video(video_path, size="2048x1152", duration_seconds=0.6)

    frames = sample_video_frames(video_path, interval_ms=500, max_frames=2)

    assert frames
    for sampled_frame in frames:
        width, height = _png_dimensions(sampled_frame.png_bytes)
        assert width <= frame_sampler.MAX_FRAME_EDGE
        assert height <= frame_sampler.MAX_FRAME_EDGE
        assert width * height <= frame_sampler.MAX_FRAME_PIXELS
        assert len(sampled_frame.png_bytes) <= frame_sampler.MAX_FRAME_PNG_BYTES
    assert sum(len(frame.png_bytes) for frame in frames) <= frame_sampler.MAX_TOTAL_FRAME_BYTES


def test_sample_video_frames_rejects_payload_over_aggregate_cap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "fixture.mp4"
    _make_video(video_path, duration_seconds=0.6)
    monkeypatch.setattr(frame_sampler, "MAX_TOTAL_FRAME_BYTES", 1)

    with pytest.raises(FramePayloadLimitError, match="payload"):
        sample_video_frames(video_path, interval_ms=500, max_frames=2)
