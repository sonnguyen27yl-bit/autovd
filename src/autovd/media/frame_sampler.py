"""Timestamped frame extraction for temporal visual analysis."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass(frozen=True, slots=True)
class SampledFrame:
    """One model-facing frame plus its source timestamp."""

    timestamp_ms: int
    png_bytes: bytes


def sample_video_frames(
    video_path: Path,
    *,
    interval_ms: int = 500,
    max_frames: int = 16,
) -> list[SampledFrame]:
    """Extract evenly spaced PNG frames from a trusted internal video path.

    External/user/model-controlled paths must be resolved and validated at the
    ingestion boundary before calling this function.
    """
    if interval_ms <= 0:
        raise ValueError("interval_ms must be greater than zero")
    if not 1 <= max_frames <= 64:
        raise ValueError("max_frames must be between 1 and 64")
    if not video_path.is_file():
        raise FileNotFoundError(video_path)

    with TemporaryDirectory(prefix="autovd-frames-") as temp_dir:
        output_pattern = str(Path(temp_dir) / "frame_%04d.png")
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps=1000/{interval_ms}",
            "-frames:v",
            str(max_frames),
            output_pattern,
        ]
        subprocess.run(command, check=True, capture_output=True, timeout=30)

        frame_paths = sorted(Path(temp_dir).glob("frame_*.png"))
        return [
            SampledFrame(timestamp_ms=index * interval_ms, png_bytes=path.read_bytes())
            for index, path in enumerate(frame_paths)
        ]
