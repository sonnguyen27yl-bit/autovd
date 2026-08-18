"""Small deterministic scorer for the temporal-anomaly MVP evaluation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabeledInterval:
    """One human-labeled temporal interval."""

    clip_id: str
    start_ms: int
    end_ms: int
    should_cut: bool
    category: str

    def __post_init__(self) -> None:
        _validate_interval(self.clip_id, self.start_ms, self.end_ms)
        if not self.category:
            raise ValueError("category must not be empty")


@dataclass(frozen=True, slots=True)
class PredictedCut:
    """One model-selected CUT interval."""

    clip_id: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        _validate_interval(self.clip_id, self.start_ms, self.end_ms)


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Precision-first metrics for the small labeled MVP set."""

    true_positive_cuts: int
    predicted_cuts: int
    cut_precision: float | None
    matched_anomalies: int
    labeled_anomalies: int
    anomaly_recall: float | None


def _validate_interval(clip_id: str, start_ms: int, end_ms: int) -> None:
    if not clip_id:
        raise ValueError("clip_id must not be empty")
    if start_ms < 0:
        raise ValueError("start_ms must be non-negative")
    if start_ms >= end_ms:
        raise ValueError("start_ms must be before end_ms")


def _overlaps(
    left_clip_id: str,
    left_start_ms: int,
    left_end_ms: int,
    right_clip_id: str,
    right_start_ms: int,
    right_end_ms: int,
) -> bool:
    return (
        left_clip_id == right_clip_id
        and left_start_ms < right_end_ms
        and right_start_ms < left_end_ms
    )


def score_cut_predictions(
    labels: list[LabeledInterval],
    predictions: list[PredictedCut],
) -> EvaluationMetrics:
    """Score predicted CUTs against human-labeled clear-anomaly intervals.

    A predicted CUT is a true positive when it overlaps at least one human interval
    marked ``should_cut=True`` in the same clip. Recall counts how many human anomaly
    intervals are overlapped by at least one predicted CUT. Ratios are undefined when
    their denominator is zero instead of being treated as an artificial perfect score.
    """
    anomaly_labels = [label for label in labels if label.should_cut]

    true_positive_cuts = sum(
        any(
            _overlaps(
                prediction.clip_id,
                prediction.start_ms,
                prediction.end_ms,
                label.clip_id,
                label.start_ms,
                label.end_ms,
            )
            for label in anomaly_labels
        )
        for prediction in predictions
    )

    matched_anomalies = sum(
        any(
            _overlaps(
                label.clip_id,
                label.start_ms,
                label.end_ms,
                prediction.clip_id,
                prediction.start_ms,
                prediction.end_ms,
            )
            for prediction in predictions
        )
        for label in anomaly_labels
    )

    predicted_count = len(predictions)
    labeled_count = len(anomaly_labels)
    return EvaluationMetrics(
        true_positive_cuts=true_positive_cuts,
        predicted_cuts=predicted_count,
        cut_precision=(true_positive_cuts / predicted_count if predicted_count else None),
        matched_anomalies=matched_anomalies,
        labeled_anomalies=labeled_count,
        anomaly_recall=(matched_anomalies / labeled_count if labeled_count else None),
    )
