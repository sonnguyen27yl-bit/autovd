"""Simple deterministic motion scoring for MVP pacing decisions."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

ANALYSIS_WIDTH = 32
ANALYSIS_HEIGHT = 32
_FRAME_BYTES = ANALYSIS_WIDTH * ANALYSIS_HEIGHT


class MotionAnalysisError(ValueError):
    """Raised when bounded motion analysis cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class MotionConfig:
    """Caller-configured MVP motion heuristic parameters."""

    frame_interval_ms: int
    threshold: float
    min_low_motion_ms: int
    speed_factor: float
    max_frames: int

    def __post_init__(self) -> None:
        if self.frame_interval_ms <= 0:
            raise ValueError("frame_interval_ms must be positive")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between zero and one")
        if self.min_low_motion_ms <= 0:
            raise ValueError("min_low_motion_ms must be positive")
        if self.speed_factor <= 1.0:
            raise ValueError("speed_factor must be greater than one")
        if self.max_frames < 2:
            raise ValueError("max_frames must be at least two")


@dataclass(frozen=True, slots=True)
class MotionScore:
    """Normalized motion observed between two sampled frame timestamps."""

    start_ms: int
    end_ms: int
    score: float

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.start_ms >= self.end_ms:
            raise ValueError("motion score interval must be positive")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("motion score must be between zero and one")


@dataclass(frozen=True, slots=True)
class SpeedRegion:
    """Sustained low-motion interval that should be accelerated."""

    start_ms: int
    end_ms: int
    speed_factor: float


def _normalized_frame_difference(left: bytes, right: bytes) -> float:
    absolute_difference = sum(
        abs(left_byte - right_byte) for left_byte, right_byte in zip(left, right, strict=True)
    )
    return absolute_difference / (255 * _FRAME_BYTES)


def measure_motion_scores(video_path: Path, config: MotionConfig) -> list[MotionScore]:
    """Measure bounded grayscale frame differences using FFmpeg only."""
    if video_path.is_symlink() or not video_path.is_file():
        raise MotionAnalysisError("motion source must be valid staged media")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        (
            f"fps=1000/{config.frame_interval_ms},"
            f"scale={ANALYSIS_WIDTH}:{ANALYSIS_HEIGHT},format=gray"
        ),
        "-frames:v",
        str(config.max_frames),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "pipe:1",
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise MotionAnalysisError("motion analysis failed") from exc

    payload = completed.stdout
    if len(payload) % _FRAME_BYTES != 0:
        raise MotionAnalysisError("motion analysis returned an invalid frame payload")
    frame_count = len(payload) // _FRAME_BYTES
    if frame_count < 2:
        return []

    frames = [
        payload[offset : offset + _FRAME_BYTES] for offset in range(0, len(payload), _FRAME_BYTES)
    ]
    return [
        MotionScore(
            start_ms=index * config.frame_interval_ms,
            end_ms=(index + 1) * config.frame_interval_ms,
            score=_normalized_frame_difference(left, right),
        )
        for index, (left, right) in enumerate(zip(frames, frames[1:], strict=False))
    ]


def detect_low_motion_regions(
    scores: list[MotionScore],
    *,
    clip_duration_ms: int,
    config: MotionConfig,
) -> list[SpeedRegion]:
    """Group sustained low-motion score intervals into speed-up regions."""
    if clip_duration_ms <= 0:
        raise ValueError("clip_duration_ms must be positive")
    if not scores:
        return []

    regions: list[SpeedRegion] = []
    active_start: int | None = None
    active_end: int | None = None

    def close_active_region() -> None:
        nonlocal active_start, active_end
        if (
            active_start is not None
            and active_end is not None
            and active_end - active_start >= config.min_low_motion_ms
        ):
            regions.append(
                SpeedRegion(
                    start_ms=active_start,
                    end_ms=active_end,
                    speed_factor=config.speed_factor,
                )
            )
        active_start = None
        active_end = None

    for sample in scores:
        if sample.start_ms >= clip_duration_ms:
            break
        sample_end = min(sample.end_ms, clip_duration_ms)
        is_low_motion = sample.score < config.threshold
        is_contiguous = active_end is None or sample.start_ms == active_end

        if is_low_motion and is_contiguous:
            if active_start is None:
                active_start = sample.start_ms
            active_end = sample_end
        else:
            close_active_region()
            if is_low_motion:
                active_start = sample.start_ms
                active_end = sample_end

    if active_start is not None and active_end is not None:
        final_observed_end = min(
            clip_duration_ms,
            active_end + config.frame_interval_ms,
        )
        active_end = final_observed_end
    close_active_region()
    return regions
