"""Synthetic-fixture-only Stage-10A source adapter firewall tests.

No original model checkpoint or C/D/D-periodic prediction is loaded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from concept_drift_ids.frozen_preprocessing import FrozenPreprocessing
from concept_drift_ids.stage10a_source_adapter import (
    DelayedLabelGate,
    ObservationStream,
    _frozen_transform,
    _select_rows,
)


def _fixture() -> pd.DataFrame:
    labels = [
        "BENIGN", "DoS GoldenEye", "Heartbleed", "BENIGN",
        "DoS GoldenEye", "BENIGN", "DoS GoldenEye", "BENIGN",
    ]
    return pd.DataFrame({
        "__row_in_source__": np.arange(10, 18, dtype=np.int64),
        " Label": labels,
        " Destination Port": np.arange(8, dtype=np.float64),
    })


def _state() -> FrozenPreprocessing:
    return FrozenPreprocessing(
        scenario_id="cicids2017_sudden_benign_v1",
        scenario_version=1,
        scenario_manifest_canonical_sha256="synthetic-only",
        feature_columns=tuple(f"f{i}" for i in range(77)),
        medians=np.full(77, 3.0),
        means=np.full(77, 1.0),
        scales=np.full(77, 2.0),
        state_hash="synthetic-only",
    )


def test_exact_selection_exclusion_order_and_binary_labels() -> None:
    selected, ids, y = _select_rows(
        _fixture(), pre_start=10, pre_end=15, post_end=18
    )
    assert ids.tolist() == [10, 11, 13, 14, 15, 16, 17]
    assert y.tolist() == [0, 1, 0, 1, 0, 1, 0]
    assert "Label" in selected
    assert selected["Label"].tolist() == [
        "BENIGN", "DoS GoldenEye", "BENIGN", "DoS GoldenEye",
        "BENIGN", "DoS GoldenEye", "BENIGN",
    ]


@pytest.mark.parametrize("bad_ids", [
    [10, 11, 11, 13, 14, 15, 16, 17],
    [10, 11, 13, 12, 14, 15, 16, 17],
    [10, 11, 12, 13, 14, 15, 16, 19],
])
def test_reordered_duplicate_missing_source_ids_fail_closed(bad_ids: list[int]) -> None:
    frame = _fixture()
    frame["__row_in_source__"] = bad_ids
    with pytest.raises(ValueError, match="missing, reordered, or duplicated"):
        _select_rows(frame, pre_start=10, pre_end=15, post_end=18)


def test_missing_source_metadata_and_whitespace_column_collisions_fail() -> None:
    with pytest.raises(ValueError, match="Source IDs absent"):
        _select_rows(_fixture().drop(columns="__row_in_source__"),
                     pre_start=10, pre_end=15, post_end=18)
    bad = _fixture()
    bad["Label"] = bad[" Label"]
    with pytest.raises(ValueError, match="collide"):
        _select_rows(bad, pre_start=10, pre_end=15, post_end=18)


def test_unfrozen_or_post_heartbleed_labels_fail_closed() -> None:
    for position, bad_label in [(1, "Bot"), (6, "Heartbleed")]:
        bad = _fixture()
        bad.loc[position, " Label"] = bad_label
        with pytest.raises(ValueError, match="Unfrozen|post exclusion"):
            _select_rows(bad, pre_start=10, pre_end=15, post_end=18)


def test_inherited_preprocessing_is_transform_only_and_is_finite() -> None:
    state = _state()
    features = pd.DataFrame(
        np.full((3, 77), 5.0), columns=state.feature_columns
    )
    features.loc[0, "f0"] = np.inf
    features.loc[1, "f1"] = np.nan
    features["Label"] = ["BENIGN"] * 3
    features["__row_in_source__"] = [11, 12, 13]
    result = _frozen_transform(features, state)
    assert result.dtype == np.float32
    assert result.shape == (3, 77)
    assert np.isfinite(result).all()
    assert result[0, 0] == 1.0  # (training median 3 - mean 1) / scale 2
    assert result[1, 1] == 1.0
    assert result[2, 2] == 2.0
    assert state.medians[0] == 3.0  # no fit/mutation of frozen state


def test_missing_feature_or_label_in_feature_schema_is_rejected() -> None:
    state = _state()
    frame = pd.DataFrame({f"f{i}": [1.0] for i in range(76)})
    with pytest.raises(ValueError, match="missing"):
        _frozen_transform(frame, state)
    invalid = FrozenPreprocessing(
        **{**state.__dict__, "feature_columns": (*state.feature_columns[:76], "Label")}
    )
    with pytest.raises(ValueError, match="Source metadata"):
        _frozen_transform(frame, invalid)


def test_unlabeled_observation_does_not_expose_provenance_or_targets() -> None:
    observations = ObservationStream(np.zeros((3, 77)))
    event = observations.observation(0)
    assert event.logical_index == 0 and len(event.features) == 77
    assert not hasattr(event, "label")
    assert not hasattr(event, "boundary")
    assert not hasattr(event, "row_in_source")
    assert not hasattr(event, "source_order")
    with pytest.raises(IndexError):
        observations.observation(3)


def test_delayed_label_is_unavailable_until_5000_later_commits() -> None:
    gate = DelayedLabelGate(np.arange(5003) % 2)
    for i in range(5000):
        assert gate.commit_prediction(i) == ()
    first = gate.commit_prediction(5000)
    assert len(first) == 1
    assert first[0].logical_index == 0
    assert first[0].binary_target == 0
    nxt = gate.commit_prediction(5001)
    assert nxt[0].logical_index == 1
    assert nxt[0].binary_target == 1


def test_gate_refuses_out_of_order_duplicate_or_invalid_latency() -> None:
    with pytest.raises(ValueError, match="exactly 5000"):
        DelayedLabelGate(np.zeros(4), latency_rows=0)
    gate = DelayedLabelGate(np.array([0, 1]))
    with pytest.raises(ValueError, match="exact stream order"):
        gate.commit_prediction(1)
    assert gate.commit_prediction(0) == ()
    with pytest.raises(ValueError, match="exact stream order"):
        gate.commit_prediction(0)
    assert gate.commit_prediction(1) == ()
    with pytest.raises(IndexError):
        gate.commit_prediction(2)


def test_gate_refuses_nonbinary_ground_truth() -> None:
    with pytest.raises(ValueError, match="0/1"):
        DelayedLabelGate(np.array([0, 2]))
