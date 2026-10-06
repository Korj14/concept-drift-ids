from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from concept_drift_ids.frozen_preprocessing import (
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.system_a import (
    SYSTEM_A_CONFIG,
    StaticMLP,
    _binary_metrics,
    select_threshold,
)


def test_frozen_preprocessing_matches_recorded_standardization_formula() -> None:
    state = load_frozen_preprocessing()

    values = state.medians.copy()
    values[0] = np.nan
    values[1] = state.medians[1] + state.scales[1]

    frame = pd.DataFrame([values], columns=state.feature_columns)
    transformed = transform_frame(frame, state, dtype=np.dtype("float64"))

    filled = values.copy()
    filled[np.isnan(filled)] = state.medians[np.isnan(filled)]
    expected = (filled - state.means) / state.scales

    np.testing.assert_allclose(transformed[0], expected, rtol=0.0, atol=1e-12)
    assert transformed.shape == (1, 77)
    assert np.isfinite(transformed).all()


def test_frozen_preprocessing_float32_output_is_finite() -> None:
    state = load_frozen_preprocessing()
    frame = pd.DataFrame(
        np.vstack([state.medians, state.means]),
        columns=state.feature_columns,
    )

    transformed = transform_frame(frame, state, dtype=np.dtype("float32"))

    assert transformed.dtype == np.float32
    assert transformed.shape == (2, 77)
    assert np.isfinite(transformed).all()


def test_static_mlp_has_frozen_shape_and_binary_logit_output() -> None:
    torch.manual_seed(0)
    model = StaticMLP()

    output = model(torch.zeros((4, 77), dtype=torch.float32))

    assert output.shape == (4,)
    assert SYSTEM_A_CONFIG["hidden_layers"] == [128, 64]
    assert SYSTEM_A_CONFIG["seeds"] == [0, 1, 2, 3, 4]


def test_threshold_selection_finds_perfect_separation() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    probabilities = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)

    threshold, metrics = select_threshold(y, probabilities)

    assert 0.2 < threshold <= 0.8
    assert metrics["mcc"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["fpr"] == 0.0


def test_binary_metrics_include_required_detection_metrics() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    probabilities = np.array([0.1, 0.7, 0.8, 0.9], dtype=np.float64)

    metrics = _binary_metrics(y, probabilities, threshold=0.5)

    assert set(metrics) == {
        "precision",
        "recall",
        "f1",
        "fpr",
        "mcc",
        "roc_auc",
        "average_precision",
    }
    assert metrics["recall"] == 1.0
    assert 0.0 <= metrics["fpr"] <= 1.0


def test_system_a_protocol_forbids_pre_post_model_development_by_design() -> None:
    assert SYSTEM_A_CONFIG["probability_calibration"] == "none"
    assert SYSTEM_A_CONFIG["early_stopping_metric"] == (
        "development_average_precision"
    )
    assert SYSTEM_A_CONFIG["threshold_objective"] == "MCC"
    assert SYSTEM_A_CONFIG["max_epochs"] == 20
