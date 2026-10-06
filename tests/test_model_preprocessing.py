from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from concept_drift_ids.model_preprocessing import (
    build_preprocessing_state,
    fit_scenario_preprocessor,
    load_preprocessing_state,
    persist_preprocessing_state,
    transform_features,
)
from concept_drift_ids.scenario_loader import (
    ScenarioPartition,
    SuddenBenignScenario,
)


def _feature_names() -> tuple[str, ...]:
    return tuple(f"f_{index:02d}" for index in range(77))


def _partition(
    name: str,
    values: np.ndarray,
    labels: list[str],
) -> ScenarioPartition:
    features = _feature_names()
    frame = pd.DataFrame(values, columns=features)

    label_series = pd.Series(labels, dtype="string", name="Label")
    target = label_series.ne("BENIGN").astype(np.int8)
    target.name = "binary_target"

    provenance = pd.DataFrame(
        {
            "scenario_partition": [name] * len(frame),
            "scenario_row": np.arange(len(frame), dtype=np.int64),
            "source_file": [f"{name}.csv"] * len(frame),
            "source_order": np.zeros(len(frame), dtype=np.int64),
            "row_in_source": np.arange(len(frame), dtype=np.int64),
            "template_source_file": [f"{name}.csv"] * len(frame),
            "template_source_order": np.zeros(len(frame), dtype=np.int64),
            "template_row_in_source": np.arange(len(frame), dtype=np.int64),
            "synthetic_replacement": np.zeros(len(frame), dtype=bool),
        }
    )

    return ScenarioPartition(
        name=name,
        X=frame,
        y=target,
        labels=label_series,
        provenance=provenance,
    )


def _manifest(training_rows: int) -> dict:
    features = list(_feature_names())

    return {
        "scenario_id": "cicids2017_sudden_benign_v1",
        "scenario_version": 1,
        "environment": {
            "python_version": "3.11.9",
            "requirements_lock_file": "requirements-lock.txt",
            "requirements_lock_sha256": "raw-lock-hash",
            "requirements_lock_normalized_text_sha256": "normalized-lock-hash",
        },
        "feature_schema": {
            "model_feature_count": 77,
            "feature_columns": features,
        },
        "partitions": {
            "training": {
                "rows": training_rows,
                "components": [
                    {
                        "source_file": "training.csv",
                        "source_order": 0,
                        "row_start_inclusive": 0,
                        "row_end_exclusive": training_rows,
                    }
                ],
                "label_counts": {
                    "BENIGN": training_rows - 1,
                    "DoS GoldenEye": 1,
                },
            }
        },
    }


def _scenario() -> SuddenBenignScenario:
    features = _feature_names()

    base = np.arange(77, dtype=np.float64)
    training_values = np.vstack(
        [
            base,
            base + 1.0,
            base + 2.0,
            base + 3.0,
        ]
    )
    training_values[1, 5] = np.nan
    training_values[3, 20] = np.nan

    development_values = np.vstack([base + 10.0, base + 11.0])
    pre_values = np.vstack([base + 20.0, base + 21.0])
    post_values = np.vstack([base + 30.0, base + 31.0])

    manifest = _manifest(training_rows=4)

    return SuddenBenignScenario(
        manifest=manifest,
        feature_columns=features,
        training=_partition(
            "training",
            training_values,
            ["BENIGN", "BENIGN", "BENIGN", "DoS GoldenEye"],
        ),
        development=_partition(
            "development",
            development_values,
            ["BENIGN", "DoS GoldenEye"],
        ),
        pre_drift=_partition(
            "pre_drift",
            pre_values,
            ["BENIGN", "DoS GoldenEye"],
        ),
        post_drift=_partition(
            "post_drift",
            post_values,
            ["BENIGN", "DoS GoldenEye"],
        ),
    )


def test_fit_uses_training_only_and_freezes_median_then_standard_scaler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "concept_drift_ids.model_preprocessing.platform.python_version",
        lambda: "3.11.9",
    )

    scenario = _scenario()
    fitted = fit_scenario_preprocessor(scenario)

    assert fitted.feature_columns == _feature_names()
    assert fitted.training_rows == 4

    expected_feature_5_median = np.median(
        scenario.training.X["f_05"].dropna().to_numpy()
    )
    assert fitted.imputer.statistics_[5] == expected_feature_5_median

    training_imputed = fitted.imputer.transform(
        scenario.training.X.to_numpy(dtype=np.float64, copy=True)
    )
    np.testing.assert_allclose(
        fitted.scaler.mean_,
        training_imputed.mean(axis=0),
    )


def test_future_mutation_cannot_change_fitted_state_or_training_transform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "concept_drift_ids.model_preprocessing.platform.python_version",
        lambda: "3.11.9",
    )

    original = _scenario()
    mutated = deepcopy(original)

    mutated.development.X.iloc[:, :] = 1.0e12
    mutated.pre_drift.X.iloc[:, :] = -1.0e12
    mutated.post_drift.X.iloc[:, :] = 7.0e11

    first = fit_scenario_preprocessor(original)
    second = fit_scenario_preprocessor(mutated)

    np.testing.assert_allclose(
        first.imputer.statistics_,
        second.imputer.statistics_,
    )
    np.testing.assert_allclose(first.scaler.mean_, second.scaler.mean_)
    np.testing.assert_allclose(first.scaler.var_, second.scaler.var_)
    np.testing.assert_allclose(first.scaler.scale_, second.scaler.scale_)

    first_training = transform_features(
        first,
        original.training.X,
        context="training",
    )
    second_training = transform_features(
        second,
        mutated.training.X,
        context="training",
    )
    np.testing.assert_allclose(first_training, second_training)


def test_transform_is_float64_finite_deterministic_and_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "concept_drift_ids.model_preprocessing.platform.python_version",
        lambda: "3.11.9",
    )

    scenario = _scenario()
    fitted = fit_scenario_preprocessor(scenario)

    before = scenario.development.X.copy(deep=True)

    first = transform_features(
        fitted,
        scenario.development.X,
        context="development",
    )
    second = transform_features(
        fitted,
        scenario.development.X,
        context="development",
    )

    assert first.dtype == np.float64
    assert first.flags["C_CONTIGUOUS"]
    assert np.isfinite(first).all()
    np.testing.assert_array_equal(first, second)
    pd.testing.assert_frame_equal(before, scenario.development.X)


def test_all_missing_training_feature_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "concept_drift_ids.model_preprocessing.platform.python_version",
        lambda: "3.11.9",
    )

    scenario = _scenario()
    scenario.training.X.loc[:, "f_10"] = np.nan

    with pytest.raises(ValueError, match="all-missing"):
        fit_scenario_preprocessor(scenario)


def test_feature_order_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "concept_drift_ids.model_preprocessing.platform.python_version",
        lambda: "3.11.9",
    )

    scenario = _scenario()
    fitted = fit_scenario_preprocessor(scenario)

    reordered = scenario.development.X.loc[
        :,
        list(reversed(scenario.development.X.columns)),
    ]

    with pytest.raises(ValueError, match="feature columns/order"):
        transform_features(
            fitted,
            reordered,
            context="development",
        )


def test_preprocessing_state_round_trip_and_tamper_detection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "concept_drift_ids.model_preprocessing.platform.python_version",
        lambda: "3.11.9",
    )

    scenario = _scenario()
    fitted = fit_scenario_preprocessor(scenario)

    fake_manifest_path = tmp_path / "scenario.json"
    fake_manifest_path.write_text(
        json.dumps(scenario.manifest, indent=2),
        encoding="utf-8",
    )

    state_path = tmp_path / "preprocessing_state.json"
    state = persist_preprocessing_state(
        fitted,
        scenario.manifest,
        path=state_path,
        manifest_path=fake_manifest_path,
    )

    loaded = load_preprocessing_state(state_path)
    assert loaded == state
    assert len(loaded["imputer"]["statistics"]) == 77
    assert len(loaded["scaler"]["mean"]) == 77
    assert len(loaded["scaler"]["var"]) == 77
    assert len(loaded["scaler"]["scale"]) == 77
    assert loaded["dtype_policy"] == {
        "shared_preprocessing_output": "float64",
        "pytorch_tensor_boundary": "float32",
    }

    tampered = dict(loaded)
    tampered["training_fit_scope"] = dict(tampered["training_fit_scope"])
    tampered["training_fit_scope"]["rows"] = 999

    state_path.write_text(
        json.dumps(tampered, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        load_preprocessing_state(state_path)


def test_build_state_records_future_partitions_as_not_used_for_fit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "concept_drift_ids.model_preprocessing.platform.python_version",
        lambda: "3.11.9",
    )

    scenario = _scenario()
    fitted = fit_scenario_preprocessor(scenario)

    fake_manifest_path = tmp_path / "scenario.json"
    fake_manifest_path.write_text(
        json.dumps(scenario.manifest, indent=2),
        encoding="utf-8",
    )

    state = build_preprocessing_state(
        fitted,
        scenario.manifest,
        manifest_path=fake_manifest_path,
    )

    fit_scope = state["training_fit_scope"]
    assert fit_scope["partition"] == "training"
    assert fit_scope["development_used_for_fit"] is False
    assert fit_scope["pre_drift_used_for_fit"] is False
    assert fit_scope["post_drift_used_for_fit"] is False
