from __future__ import annotations

import csv
import json

import numpy as np
import pandas as pd
import torch

import concept_drift_ids.system_a as system_a
from concept_drift_ids.evaluation_tables import write_evaluation_tables
from concept_drift_ids.frozen_preprocessing import (
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.neural import (
    BinaryMLP,
    binary_metrics,
    mean_ci95,
    select_mcc_threshold,
)
from concept_drift_ids.system_a import SYSTEM_A_CONFIG


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
    model = BinaryMLP(
        input_features=77,
        hidden_layers=(128, 64),
        dropout=0.10,
    )

    output = model(torch.zeros((4, 77), dtype=torch.float32))

    assert output.shape == (4,)
    assert SYSTEM_A_CONFIG["hidden_layers"] == [128, 64]
    assert SYSTEM_A_CONFIG["seeds"] == [0, 1, 2, 3, 4]


def test_threshold_selection_finds_perfect_separation() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    probabilities = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)

    threshold, metrics = select_mcc_threshold(y, probabilities)

    assert 0.2 < threshold <= 0.8
    assert metrics["mcc"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["fpr"] == 0.0


def test_binary_metrics_include_required_detection_metrics() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    probabilities = np.array([0.1, 0.7, 0.8, 0.9], dtype=np.float64)

    metrics = binary_metrics(y, probabilities, threshold=0.5)

    assert set(metrics) == {
        "accuracy",
        "balanced_accuracy",
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


def test_mean_ci95_exposes_plot_ready_summary_fields() -> None:
    summary = mean_ci95([0.5, 0.6, 0.7, 0.8, 0.9])

    assert summary["n"] == 5
    assert summary["mean"] == 0.7
    assert summary["std"] > 0.0
    assert summary["ci95_low"] < summary["mean"] < summary["ci95_high"]


def test_evaluation_tables_are_long_form_and_combinable(tmp_path) -> None:
    summary = {
        "n": 2,
        "mean": 0.75,
        "std": 0.05,
        "ci95_low": 0.70,
        "ci95_high": 0.80,
    }
    results = {
        "system_id": "system_a_static_neural_v1",
        "scenario_id": "scenario",
        "scenario_version": 1,
        "partitions": {
            "pre_drift": {
                "seed_results": [
                    {
                        "seed": 0,
                        "threshold": 0.9,
                        "metrics": {"mcc": 0.7},
                    },
                    {
                        "seed": 1,
                        "threshold": 0.8,
                        "metrics": {"mcc": 0.8},
                    },
                ],
                "aggregate": {"mcc": summary},
            },
            "post_drift": {
                "seed_results": [
                    {
                        "seed": 0,
                        "threshold": 0.9,
                        "metrics": {"mcc": 0.6},
                    },
                    {
                        "seed": 1,
                        "threshold": 0.8,
                        "metrics": {"mcc": 0.7},
                    },
                ],
                "aggregate": {"mcc": summary},
            },
        },
        "post_minus_pre": {
            "seed_deltas": [
                {"seed": 0, "metrics": {"mcc": -0.1}},
                {"seed": 1, "metrics": {"mcc": -0.1}},
            ],
            "aggregate": {"mcc": summary},
        },
    }

    paths = write_evaluation_tables(results, tmp_path)

    assert all(path.exists() for path in paths.values())

    with paths["metrics_by_seed"].open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 4
    assert set(rows[0]) == {
        "system_id",
        "scenario_id",
        "scenario_version",
        "partition",
        "seed",
        "threshold",
        "metric",
        "value",
    }


def test_evaluation_manifest_verifier_checks_hash_linked_files(
    tmp_path,
    monkeypatch,
) -> None:
    artifact = tmp_path / "artifact.csv"
    artifact.write_text("a,b\n1,2\n", encoding="utf-8")

    from concept_drift_ids.scenario_manifest import sha256_file

    manifest = {
        "manifest_format_version": 1,
        "evaluation_id": "test",
        "system_id": "system_a_static_neural_v1",
        "scenario_id": "scenario",
        "scenario_version": 1,
        "system_manifest_sha256": "system-hash",
        "preprocessing_state_hash": "preprocessing-hash",
        "files": {
            "artifact": {
                "path": "artifact.csv",
                "sha256": sha256_file(artifact),
            }
        },
    }
    manifest["manifest_sha256"] = system_a._json_hash(manifest)

    manifest_path = tmp_path / "evaluation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(system_a, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        system_a,
        "EVALUATION_MANIFEST_PATH",
        manifest_path,
    )

    verified = system_a._load_and_verify_evaluation_manifest(
        {"manifest_sha256": "system-hash"},
        preprocessing_hash="preprocessing-hash",
    )

    assert verified["manifest_sha256"] == manifest["manifest_sha256"]
