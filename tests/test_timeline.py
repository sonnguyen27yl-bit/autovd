import pytest

from autovd.contracts.edit_plan import CutInterval
from autovd.media.motion import SpeedRegion
from autovd.media.timeline import build_render_segments


def test_build_render_segments_keeps_full_clip_without_edits() -> None:
    segments = build_render_segments(clip_duration_ms=3000, cuts=[], speed_regions=[])

    assert [(segment.start_ms, segment.end_ms, segment.speed_factor) for segment in segments] == [
        (0, 3000, 1.0)
    ]


def test_cut_takes_precedence_over_overlapping_speed_region() -> None:
    segments = build_render_segments(
        clip_duration_ms=4000,
        cuts=[CutInterval(start_ms=1000, end_ms=2000)],
        speed_regions=[SpeedRegion(start_ms=500, end_ms=3000, speed_factor=2.0)],
    )

    assert [(segment.start_ms, segment.end_ms, segment.speed_factor) for segment in segments] == [
        (0, 500, 1.0),
        (500, 1000, 2.0),
        (2000, 3000, 2.0),
        (3000, 4000, 1.0),
    ]


def test_adjacent_segments_with_same_speed_are_combined() -> None:
    segments = build_render_segments(
        clip_duration_ms=3000,
        cuts=[],
        speed_regions=[
            SpeedRegion(start_ms=500, end_ms=1500, speed_factor=2.0),
            SpeedRegion(start_ms=1500, end_ms=2500, speed_factor=2.0),
        ],
    )

    assert [(segment.start_ms, segment.end_ms, segment.speed_factor) for segment in segments] == [
        (0, 500, 1.0),
        (500, 2500, 2.0),
        (2500, 3000, 1.0),
    ]


def test_fully_cut_clip_has_no_render_segments() -> None:
    assert (
        build_render_segments(
            clip_duration_ms=1000,
            cuts=[CutInterval(start_ms=0, end_ms=1000)],
            speed_regions=[],
        )
        == []
    )


def test_out_of_range_speed_region_is_rejected() -> None:
    with pytest.raises(ValueError, match="speed region"):
        build_render_segments(
            clip_duration_ms=1000,
            cuts=[],
            speed_regions=[SpeedRegion(start_ms=500, end_ms=1200, speed_factor=2.0)],
        )
