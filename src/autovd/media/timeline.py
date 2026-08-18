"""Deterministic render timeline construction from validated edit decisions."""

from dataclasses import dataclass

from autovd.contracts.edit_plan import CutInterval, merge_cut_intervals
from autovd.media.motion import SpeedRegion


@dataclass(frozen=True, slots=True)
class RenderSegment:
    """One source interval retained in output at the given playback speed."""

    start_ms: int
    end_ms: int
    speed_factor: float

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.start_ms >= self.end_ms:
            raise ValueError("render segment interval must be positive")
        if self.speed_factor < 1.0:
            raise ValueError("render segment speed_factor must be at least one")


def _validate_speed_regions(
    speed_regions: list[SpeedRegion],
    *,
    clip_duration_ms: int,
) -> list[SpeedRegion]:
    ordered = sorted(speed_regions, key=lambda region: (region.start_ms, region.end_ms))
    previous_end: int | None = None
    for region in ordered:
        if region.start_ms < 0 or region.start_ms >= region.end_ms:
            raise ValueError("speed region interval must be positive")
        if region.end_ms > clip_duration_ms:
            raise ValueError("speed region exceeds clip duration")
        if region.speed_factor <= 1.0:
            raise ValueError("speed region speed_factor must be greater than one")
        if previous_end is not None and region.start_ms < previous_end:
            raise ValueError("speed regions must not overlap")
        previous_end = region.end_ms
    return ordered


def build_render_segments(
    *,
    clip_duration_ms: int,
    cuts: list[CutInterval],
    speed_regions: list[SpeedRegion],
) -> list[RenderSegment]:
    """Build retained timeline segments with CUT taking precedence over speed-up."""
    if clip_duration_ms <= 0:
        raise ValueError("clip_duration_ms must be positive")

    merged_cuts = merge_cut_intervals(cuts)
    for cut in merged_cuts:
        if cut.end_ms > clip_duration_ms:
            raise ValueError("cut interval exceeds clip duration")
    ordered_speed_regions = _validate_speed_regions(
        speed_regions,
        clip_duration_ms=clip_duration_ms,
    )

    boundaries = {0, clip_duration_ms}
    for cut in merged_cuts:
        boundaries.add(cut.start_ms)
        boundaries.add(cut.end_ms)
    for region in ordered_speed_regions:
        boundaries.add(region.start_ms)
        boundaries.add(region.end_ms)
    ordered_boundaries = sorted(boundaries)

    segments: list[RenderSegment] = []
    for start_ms, end_ms in zip(ordered_boundaries, ordered_boundaries[1:], strict=False):
        if any(cut.start_ms <= start_ms and end_ms <= cut.end_ms for cut in merged_cuts):
            continue

        speed_factor = 1.0
        for region in ordered_speed_regions:
            if region.start_ms <= start_ms and end_ms <= region.end_ms:
                speed_factor = region.speed_factor
                break

        if (
            segments
            and segments[-1].end_ms == start_ms
            and segments[-1].speed_factor == speed_factor
        ):
            previous = segments[-1]
            segments[-1] = RenderSegment(
                start_ms=previous.start_ms,
                end_ms=end_ms,
                speed_factor=speed_factor,
            )
        else:
            segments.append(
                RenderSegment(
                    start_ms=start_ms,
                    end_ms=end_ms,
                    speed_factor=speed_factor,
                )
            )

    return segments
