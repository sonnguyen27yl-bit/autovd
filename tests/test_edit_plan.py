import pytest
from pydantic import ValidationError

from autovd.contracts.edit_plan import (
    AnomalyCategory,
    CutCandidate,
    CutCertainty,
    EditPlanLimits,
    validate_cut_candidates,
)


def _candidate(
    *,
    start_ms: int,
    end_ms: int,
    certainty: CutCertainty = CutCertainty.CLEAR,
) -> CutCandidate:
    return CutCandidate(
        clip_id="clip_0000",
        start_ms=start_ms,
        end_ms=end_ms,
        category=AnomalyCategory.MELT_OR_GLITCH,
        certainty=certainty,
    )


def test_uncertain_candidate_is_kept_not_cut() -> None:
    cuts = validate_cut_candidates(
        [_candidate(start_ms=1000, end_ms=1500, certainty=CutCertainty.UNCERTAIN)],
        clip_id="clip_0000",
        clip_duration_ms=3000,
        limits=EditPlanLimits(max_cut_intervals=8),
    )

    assert cuts == []


def test_clear_overlapping_and_touching_candidates_are_merged() -> None:
    cuts = validate_cut_candidates(
        [
            _candidate(start_ms=1000, end_ms=1500),
            _candidate(start_ms=1400, end_ms=1800),
            _candidate(start_ms=1800, end_ms=2000),
        ],
        clip_id="clip_0000",
        clip_duration_ms=3000,
        limits=EditPlanLimits(max_cut_intervals=8),
    )

    assert [(cut.start_ms, cut.end_ms) for cut in cuts] == [(1000, 2000)]


def test_candidate_outside_clip_is_rejected_even_when_uncertain() -> None:
    with pytest.raises(ValueError, match="clip duration"):
        validate_cut_candidates(
            [_candidate(start_ms=2500, end_ms=3500, certainty=CutCertainty.UNCERTAIN)],
            clip_id="clip_0000",
            clip_duration_ms=3000,
            limits=EditPlanLimits(max_cut_intervals=8),
        )


def test_candidate_for_another_clip_is_rejected() -> None:
    candidate = _candidate(start_ms=100, end_ms=200).model_copy(update={"clip_id": "clip_other"})

    with pytest.raises(ValueError, match="clip_id"):
        validate_cut_candidates(
            [candidate],
            clip_id="clip_0000",
            clip_duration_ms=3000,
            limits=EditPlanLimits(max_cut_intervals=8),
        )


def test_candidate_schema_rejects_unknown_category_and_invalid_range() -> None:
    with pytest.raises(ValidationError):
        CutCandidate(
            clip_id="clip_0000",
            start_ms=1000,
            end_ms=900,
            category="NOT_AN_MVP_CATEGORY",
            certainty="clear",
        )


def test_candidate_count_is_bounded_before_execution() -> None:
    with pytest.raises(ValueError, match="cut interval count"):
        validate_cut_candidates(
            [
                _candidate(start_ms=0, end_ms=100),
                _candidate(start_ms=200, end_ms=300),
            ],
            clip_id="clip_0000",
            clip_duration_ms=1000,
            limits=EditPlanLimits(max_cut_intervals=1),
        )
