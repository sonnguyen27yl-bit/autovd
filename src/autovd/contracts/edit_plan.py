"""Typed conservative CUT contracts for model-generated edit decisions."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnomalyCategory(StrEnum):
    """Visual-generation failures that the MVP may remove."""

    ANATOMY_DEFORMATION = "ANATOMY_DEFORMATION"
    FACE_DEFORMATION = "FACE_DEFORMATION"
    IDENTITY_BREAK = "IDENTITY_BREAK"
    OBJECT_MUTATION = "OBJECT_MUTATION"
    OBJECT_APPEAR_DISAPPEAR = "OBJECT_APPEAR_DISAPPEAR"
    OBJECT_INTERSECTION = "OBJECT_INTERSECTION"
    BACKGROUND_BREAK = "BACKGROUND_BREAK"
    MELT_OR_GLITCH = "MELT_OR_GLITCH"
    IMPOSSIBLE_MOTION = "IMPOSSIBLE_MOTION"
    OTHER_OBVIOUS_GENERATION_ERROR = "OTHER_OBVIOUS_GENERATION_ERROR"


class CutCertainty(StrEnum):
    """Confidence gate used by the conservative full-auto MVP."""

    CLEAR = "clear"
    UNCERTAIN = "uncertain"


class CutCandidate(BaseModel):
    """One untrusted model-selected candidate interval."""

    model_config = ConfigDict(extra="forbid")

    clip_id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    category: AnomalyCategory
    certainty: CutCertainty

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be before end_ms")
        return self


@dataclass(frozen=True, slots=True, order=True)
class CutInterval:
    """Validated final CUT interval consumed by deterministic backend logic."""

    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        if self.start_ms < 0:
            raise ValueError("start_ms must be non-negative")
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be before end_ms")


@dataclass(frozen=True, slots=True)
class EditPlanLimits:
    """Caller-configured limits for model-generated CUT candidates."""

    max_cut_intervals: int

    def __post_init__(self) -> None:
        if self.max_cut_intervals <= 0:
            raise ValueError("max_cut_intervals must be positive")


def merge_cut_intervals(intervals: list[CutInterval]) -> list[CutInterval]:
    """Sort and merge overlapping or touching validated CUT intervals."""
    if not intervals:
        return []

    ordered = sorted(intervals)
    merged: list[CutInterval] = [ordered[0]]
    for interval in ordered[1:]:
        current = merged[-1]
        if interval.start_ms <= current.end_ms:
            merged[-1] = CutInterval(
                start_ms=current.start_ms,
                end_ms=max(current.end_ms, interval.end_ms),
            )
        else:
            merged.append(interval)
    return merged


def validate_cut_candidates(
    candidates: list[CutCandidate],
    *,
    clip_id: str,
    clip_duration_ms: int,
    limits: EditPlanLimits,
) -> list[CutInterval]:
    """Validate all candidates, then keep and merge only clear CUT decisions."""
    if not clip_id:
        raise ValueError("clip_id must not be empty")
    if clip_duration_ms <= 0:
        raise ValueError("clip duration must be positive")
    if len(candidates) > limits.max_cut_intervals:
        raise ValueError("cut interval count exceeds configured limit")

    clear_intervals: list[CutInterval] = []
    for candidate in candidates:
        if candidate.clip_id != clip_id:
            raise ValueError("candidate clip_id does not match target clip_id")
        if candidate.end_ms > clip_duration_ms:
            raise ValueError("candidate interval exceeds clip duration")
        if candidate.certainty is CutCertainty.CLEAR:
            clear_intervals.append(
                CutInterval(start_ms=candidate.start_ms, end_ms=candidate.end_ms)
            )

    return merge_cut_intervals(clear_intervals)
