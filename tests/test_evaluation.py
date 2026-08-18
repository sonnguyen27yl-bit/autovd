from autovd.evaluation import LabeledInterval, PredictedCut, score_cut_predictions


def test_score_cut_predictions_counts_overlap_per_predicted_cut() -> None:
    labels = [
        LabeledInterval(
            clip_id="clip-a",
            start_ms=1000,
            end_ms=2000,
            should_cut=True,
            category="ANATOMY_DEFORMATION",
        ),
        LabeledInterval(
            clip_id="clip-a",
            start_ms=3000,
            end_ms=3500,
            should_cut=True,
            category="OBJECT_MUTATION",
        ),
        LabeledInterval(
            clip_id="clip-b",
            start_ms=0,
            end_ms=1000,
            should_cut=False,
            category="CLEAN",
        ),
    ]
    predictions = [
        PredictedCut(clip_id="clip-a", start_ms=1200, end_ms=1600),
        PredictedCut(clip_id="clip-a", start_ms=5000, end_ms=5500),
    ]

    metrics = score_cut_predictions(labels, predictions)

    assert metrics.true_positive_cuts == 1
    assert metrics.predicted_cuts == 2
    assert metrics.cut_precision == 0.5
    assert metrics.matched_anomalies == 1
    assert metrics.labeled_anomalies == 2
    assert metrics.anomaly_recall == 0.5


def test_score_cut_predictions_does_not_match_across_clips() -> None:
    labels = [
        LabeledInterval(
            clip_id="clip-a",
            start_ms=1000,
            end_ms=2000,
            should_cut=True,
            category="GLITCH",
        )
    ]
    predictions = [PredictedCut(clip_id="clip-b", start_ms=1000, end_ms=2000)]

    metrics = score_cut_predictions(labels, predictions)

    assert metrics.cut_precision == 0.0
    assert metrics.anomaly_recall == 0.0


def test_score_cut_predictions_reports_undefined_ratios_when_denominator_is_zero() -> None:
    metrics = score_cut_predictions([], [])

    assert metrics.cut_precision is None
    assert metrics.anomaly_recall is None


def test_interval_models_reject_invalid_ranges() -> None:
    try:
        PredictedCut(clip_id="clip-a", start_ms=1000, end_ms=1000)
    except ValueError:
        pass
    else:
        raise AssertionError("zero-length predicted cut must be rejected")
