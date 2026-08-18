import subprocess
from pathlib import Path

import pytest
from autovd.media.motion import (
    MotionConfig,
    MotionScore,
    detect_low_motion_regions,
    measure_motion_scores,
)


def _make_video(path: Path, source: str) -> None:
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
            source,
            "-an",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _config() -> MotionConfig:
    return MotionConfig(
        frame_interval_ms=200,
        threshold=0.01,
        min_low_motion_ms=800,
        speed_factor=2.0,
        max_frames=32,
    )


def test_measure_motion_scores_separates_static_and_moving_synthetic_video(
    tmp_path: Path,
) -> None:
    static_path = tmp_path / "static.mp4"
    moving_path = tmp_path / "moving.mp4"
    _make_video(static_path, "color=c=black:s=64x64:r=5:d=2")
    _make_video(moving_path, "testsrc2=s=64x64:r=5:d=2")

    static_scores = measure_motion_scores(static_path, _config())
    moving_scores = measure_motion_scores(moving_path, _config())

    assert static_scores
    assert all(sample.score == 0.0 for sample in static_scores)
    assert moving_scores
    assert max(sample.score for sample in moving_scores) > _config().threshold


def test_detect_low_motion_regions_groups_only_sustained_low_motion() -> None:
    config = MotionConfig(
        frame_interval_ms=500,
        threshold=0.01,
        min_low_motion_ms=1000,
        speed_factor=1.75,
        max_frames=16,
    )
    scores = [
        MotionScore(start_ms=0, end_ms=500, score=0.0),
        MotionScore(start_ms=500, end_ms=1000, score=0.005),
        MotionScore(start_ms=1000, end_ms=1500, score=0.05),
        MotionScore(start_ms=1500, end_ms=2000, score=0.0),
    ]

    regions = detect_low_motion_regions(scores, clip_duration_ms=2500, config=config)

    assert [(region.start_ms, region.end_ms, region.speed_factor) for region in regions] == [
        (0, 1000, 1.75),
        (1500, 2500, 1.75),
    ]


def test_short_low_motion_run_is_not_accelerated() -> None:
    config = MotionConfig(
        frame_interval_ms=500,
        threshold=0.01,
        min_low_motion_ms=1000,
        speed_factor=2.0,
        max_frames=16,
    )
    scores = [
        MotionScore(start_ms=0, end_ms=500, score=0.0),
        MotionScore(start_ms=500, end_ms=1000, score=0.05),
    ]

    assert detect_low_motion_regions(scores, clip_duration_ms=1000, config=config) == []


def test_motion_config_rejects_non_accelerating_speed() -> None:
    with pytest.raises(ValueError, match="speed_factor"):
        MotionConfig(
            frame_interval_ms=500,
            threshold=0.01,
            min_low_motion_ms=1000,
            speed_factor=1.0,
            max_frames=16,
        )
