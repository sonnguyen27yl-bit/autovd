"""Timestamped frame extraction for temporal visual analysis."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

MAX_FRAME_EDGE = 640
MAX_FRAME_PIXELS = MAX_FRAME_EDGE * MAX_FRAME_EDGE
MAX_FRAME_PNG_BYTES = 2 * 1024 * 1024
MAX_TOTAL_FRAME_BYTES = 12 * 1024 * 1024


class FramePayloadLimitError(RuntimeError):
    """Raised when model-facing temporal evidence exceeds configured safety bounds."""


@dataclass(frozen=True, slots=True)
class SampledFrame:
    """One model-facing frame plus its source timestamp."""

    timestamp_ms: int
    png_bytes: bytes


def _png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    if len(png_bytes) < 24 or not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise FramePayloadLimitError("invalid analysis frame payload")
    return (
        int.from_bytes(png_bytes[16:20], "big"),
        int.from_bytes(png_bytes[20:24], "big"),
    )


def sample_video_frames(
    video_path: Path,
    *,
    interval_ms: int = 500,
    max_frames: int = 16,
    start_ms: int = 0,
    end_ms: int | None = None,
) -> list[SampledFrame]:
    """Extract bounded, evenly spaced PNG frames from a trusted internal video path."""
    if interval_ms <= 0:
        raise ValueError("interval_ms must be greater than zero")
    if not 1 <= max_frames <= 64:
        raise ValueError("max_frames must be between 1 and 64")
    if start_ms < 0:
        raise ValueError("start_ms must be non-negative")
    if end_ms is not None and end_ms <= start_ms:
        raise ValueError("end_ms must be greater than start_ms")
    if not video_path.is_file():
        raise FileNotFoundError(video_path)

    with TemporaryDirectory(prefix="autovd-frames-") as temp_dir:
        output_pattern = str(Path(temp_dir) / "frame_%04d.png")
        scale_filter = (
            f"scale='min({MAX_FRAME_EDGE},iw)':'min({MAX_FRAME_EDGE},ih)':"
            "force_original_aspect_ratio=decrease"
        )
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
        ]
        if start_ms:
            command.extend(["-ss", f"{start_ms / 1000:.3f}"])
        command.extend(["-i", str(video_path)])
        if end_ms is not None:
            command.extend(["-t", f"{(end_ms - start_ms) / 1000:.3f}"])
        command.extend(
            [
                "-vf",
                f"fps=1000/{interval_ms},{scale_filter}",
                "-frames:v",
                str(max_frames),
                output_pattern,
            ]
        )
        subprocess.run(command, check=True, capture_output=True, timeout=30)

        frames: list[SampledFrame] = []
        total_bytes = 0
        for index, path in enumerate(sorted(Path(temp_dir).glob("frame_*.png"))):
            encoded_bytes = path.stat().st_size
            if encoded_bytes > MAX_FRAME_PNG_BYTES:
                raise FramePayloadLimitError("frame payload exceeds configured limit")
            total_bytes += encoded_bytes
            if total_bytes > MAX_TOTAL_FRAME_BYTES:
                raise FramePayloadLimitError("aggregate frame payload exceeds configured limit")

            png_bytes = path.read_bytes()
            width, height = _png_dimensions(png_bytes)
            if (
                width > MAX_FRAME_EDGE
                or height > MAX_FRAME_EDGE
                or width * height > MAX_FRAME_PIXELS
            ):
                raise FramePayloadLimitError("frame dimensions exceed configured limit")

            frames.append(
                SampledFrame(
                    timestamp_ms=start_ms + index * interval_ms,
                    png_bytes=png_bytes,
                )
            )

        return frames
