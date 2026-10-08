from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
import torch

from concept_drift_ids.cd_control_plane import (
    ADWIN_CONFIG,
    ANCHOR_SEED,
    PRIMARY_LABEL_LATENCY,
    DelayedLabelQueue,
    DetectorObservation,
    MatureLabelRecord,
    NeuralUpdateConfig,
    ReservoirItem,
    SharedErrorDriftMonitor,
    UniformReservoir,
    adapt_neural_checkpoint,
    assert_no_boundary_contamination,
    row_ids_sha256,
    select_recent_current_evidence,
    select_replay_ids,
    select_uniform_anchor_ids,
    state_dict_sha256,
    verify_checkpoint_purity,
    verify_information_timing,
    verify_shared_control_plane_identity,
    write_checkpoint_new,
    write_json_new,
)
from concept_drift_ids.neural import BinaryMLP


def _mature(
    i: int,
    *,
    checkpoint: str = "parent",
    latency: int = 5,
    probability: float = 0.1,
    label: int = 0,
) -> MatureLabelRecord:
    return MatureLabelRecord(
        row_id=f"row-{i}",
        origin_index=i,
        maturity_index=i + latency,
        checkpoint_sha256=checkpoint,
        neural_probability=probability,
        true_label=label,
    )


def test_primary_latency_is_frozen_to_5000() -> None:
    assert PRIMARY_LABEL_LATENCY == 5_000


def test_label_release_requires_same_clock_prediction_commit() -> None:
    queue = DelayedLabelQueue(latency=2)
    queue.commit_prediction(
        row_id="r0",
        origin_index=0,
        checkpoint_sha256="a",
        neural_probability=0.1,
        true_label=0,
    )
    with pytest.raises(RuntimeError, match="prediction"):
        queue.release_after_prediction(2)


def test_prediction_before_release_and_zero_delay_semantics() -> None:
    queue = DelayedLabelQueue(latency=0)
    queue.commit_prediction(
        row_id="r0",
        origin_index=0,
        checkpoint_sha256="a",
        neural_probability=0.9,
        true_label=1,
    )
    released = queue.release_after_prediction(0)
    assert len(released) == 1
    assert released[0].origin_index == 0
    assert released[0].maturity_index == 0


def test_delayed_queue_does_not_flush_pending_labels() -> None:
    queue = DelayedLabelQueue(latency=5)
    for i in range(3):
        queue.commit_prediction(
            row_id=f"r{i}",
            origin_index=i,
            checkpoint_sha256="a",
            neural_probability=0.1,
            true_label=0,
        )
    assert queue.pending_count() == 3
    assert queue.pending_origin_indices() == [0, 1, 2]


def test_uniform_reservoir_is_deterministic() -> None:
    items = [
        ReservoirItem(
            row_id=f"r{i}",
            origin_index=i,
            maturity_index=i + 5,
            checkpoint_sha256="a",
            label=i % 2,
        )
        for i in range(100)
    ]
    left = UniformReservoir(capacity=10, seed=123)
    right = UniformReservoir(capacity=10, seed=123)
    for item in items:
        left.consider(item)
        right.consider(item)
    assert left.row_ids() == right.row_ids()
    assert left.identity_sha256() == right.identity_sha256()
    assert left.seen == 100


def test_anchor_selection_is_uniform_position_sampling_and_deterministic() -> None:
    row_ids = [f"train-{i}" for i in range(100)]
    first = select_uniform_anchor_ids(row_ids, capacity=20, seed=ANCHOR_SEED)
    second = select_uniform_anchor_ids(row_ids, capacity=20, seed=ANCHOR_SEED)
    assert first == second
    assert len(first) == 20
    assert len(set(first)) == 20


def test_current_evidence_requires_mature_parent_checkpoint_rows() -> None:
    records = [_mature(i, checkpoint="parent") for i in range(8)]
    records += [_mature(8, checkpoint="old"), _mature(9, checkpoint="parent")]
    selected = select_recent_current_evidence(
        records,
        parent_checkpoint_sha256="parent",
        action_clock=12,
        window_size=4,
    )
    assert selected is not None
    assert [item.row_id for item in selected] == [
        "row-4",
        "row-5",
        "row-6",
        "row-7",
    ]


def test_current_evidence_returns_none_instead_of_shrinking_budget() -> None:
    records = [_mature(i, checkpoint="parent") for i in range(3)]
    assert (
        select_recent_current_evidence(
            records,
            parent_checkpoint_sha256="parent",
            action_clock=20,
            window_size=4,
        )
        is None
    )


def test_replay_selection_is_deterministic_and_disjoint_from_current() -> None:
    anchor = [f"a-{i}" for i in range(20)]
    online = [
        ReservoirItem(
            row_id=f"o-{i}",
            origin_index=i,
            maturity_index=i + 5,
            checkpoint_sha256="p",
            label=i % 2,
        )
        for i in range(20)
    ]
    current = {"o-0", "o-1"}
    first = select_replay_ids(
        anchor_ids=anchor,
        online_items=online,
        current_row_ids=current,
        event_id=1,
        anchor_rows=3,
        online_rows=3,
    )
    second = select_replay_ids(
        anchor_ids=anchor,
        online_items=online,
        current_row_ids=current,
        event_id=1,
        anchor_rows=3,
        online_rows=3,
    )
    assert first == second
    assert len(first) == 6
    assert not set(first).intersection(current)


class _FakeADWIN:
    def __init__(self) -> None:
        self.count = 0
        self.drift_detected = False

    def update(self, _: int) -> None:
        self.count += 1
        self.drift_detected = self.count >= 2


def test_detector_disarms_on_event_and_quarantines_old_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        SharedErrorDriftMonitor,
        "_new_adwin",
        staticmethod(lambda: _FakeADWIN()),
    )
    monitor = SharedErrorDriftMonitor(monitor_threshold=0.5)
    monitor.start_initial_epoch("parent")

    first = monitor.observe(_mature(0, checkpoint="parent", probability=0.9, label=0))
    second = monitor.observe(_mature(1, checkpoint="parent", probability=0.9, label=0))
    assert first.admitted and not first.drift_detected
    assert second.admitted and second.drift_detected
    assert monitor.disarmed

    while_disarmed = monitor.observe(_mature(2, checkpoint="parent"))
    assert not while_disarmed.admitted
    assert while_disarmed.reason == "detector_disarmed"

    monitor.publish_child_checkpoint("child")
    stale = monitor.observe(_mature(3, checkpoint="parent"))
    assert not stale.admitted
    assert stale.reason == "stale_checkpoint_error"

    child = monitor.observe(_mature(4, checkpoint="child"))
    assert child.admitted
    assert child.epoch_checkpoint_sha256 == "child"


def test_adwin_primary_configuration_is_locked() -> None:
    assert ADWIN_CONFIG == {
        "delta": 0.002,
        "clock": 32,
        "max_buckets": 5,
        "min_window_length": 5,
        "grace_period": 10,
    }


def test_checkpoint_purity_verifier_rejects_impure_admission() -> None:
    observation = DetectorObservation(
        row_id="x",
        origin_index=1,
        maturity_index=6,
        epoch_id=2,
        epoch_checkpoint_sha256="child",
        prediction_checkpoint_sha256="parent",
        error=1,
        admitted=True,
        drift_detected=False,
        reason="admitted",
    )
    with pytest.raises(ValueError, match="impure"):
        verify_checkpoint_purity([observation])


def test_information_timing_rejects_future_or_pending_evidence() -> None:
    with pytest.raises(ValueError, match="Future"):
        verify_information_timing(
            [{"logical_clock": 10, "origin_index": 11, "label_required": False}]
        )
    with pytest.raises(ValueError, match="Pending"):
        verify_information_timing(
            [
                {
                    "logical_clock": 10,
                    "origin_index": 5,
                    "maturity_index": 11,
                    "label_required": True,
                }
            ]
        )


def test_shared_control_plane_identity_fails_closed() -> None:
    base = {
        "label_schedule_sha256": "a",
        "detector_events_sha256": "b",
        "replay_evidence_sha256": "c",
        "checkpoint_chain_sha256": "d",
    }
    verify_shared_control_plane_identity(base, dict(base))
    changed = dict(base, checkpoint_chain_sha256="different")
    with pytest.raises(ValueError, match="checkpoint_chain"):
        verify_shared_control_plane_identity(base, changed)


def test_boundary_fields_are_rejected_recursively() -> None:
    assert_no_boundary_contamination({"event": {"logical_clock": 3}})
    with pytest.raises(ValueError, match="boundary"):
        assert_no_boundary_contamination(
            {"event": {"logical_clock": 3, "synthetic_boundary": 10}}
        )


def test_neural_update_is_deterministic_from_same_parent_and_evidence() -> None:
    torch.manual_seed(7)
    parent = BinaryMLP(input_features=3, hidden_layers=(4, 2), dropout=0.1)
    X_current = np.array(
        [[0.0, 0.1, 0.2], [0.2, 0.1, 0.0], [1.0, 1.0, 1.0], [0.9, 1.0, 1.1]],
        dtype=np.float32,
    )
    y_current = np.array([0, 0, 1, 1], dtype=np.int8)
    X_replay = np.array(
        [[0.1, 0.2, 0.1], [0.3, 0.2, 0.1], [1.1, 1.0, 0.9], [1.2, 1.1, 1.0]],
        dtype=np.float32,
    )
    y_replay = np.array([0, 0, 1, 1], dtype=np.int8)
    config = NeuralUpdateConfig(
        learning_rate=1e-3,
        weight_decay=0.0,
        batch_size=4,
        epochs=2,
        pos_weight=1.0,
    )

    left = adapt_neural_checkpoint(
        parent,
        X_current=X_current,
        y_current=y_current,
        X_replay=X_replay,
        y_replay=y_replay,
        seed=2,
        event_id=1,
        config=config,
    )
    right = adapt_neural_checkpoint(
        parent,
        X_current=X_current,
        y_current=y_current,
        X_replay=X_replay,
        y_replay=y_replay,
        seed=2,
        event_id=1,
        config=config,
    )
    assert left.state_sha256 == right.state_sha256
    assert left.epoch_losses == pytest.approx(right.epoch_losses, abs=0.0, rel=0.0)
    assert state_dict_sha256(parent) != left.state_sha256


def test_write_once_artifacts_refuse_overwrite(tmp_path) -> None:
    json_path = tmp_path / "event.json"
    write_json_new(json_path, {"schema_version": 1, "event": "x"})
    with pytest.raises(FileExistsError, match="overwrite"):
        write_json_new(json_path, {"schema_version": 1, "event": "y"})

    torch.manual_seed(3)
    model = BinaryMLP(input_features=3, hidden_layers=(4, 2), dropout=0.1)
    checkpoint_path = tmp_path / "child.pt"
    info = write_checkpoint_new(
        checkpoint_path,
        model=model,
        metadata={"parent": "root"},
    )
    assert info["state_sha256"] == state_dict_sha256(model)
    with pytest.raises(FileExistsError, match="overwrite"):
        write_checkpoint_new(
            checkpoint_path,
            model=model,
            metadata={"parent": "root"},
        )


def test_row_identity_hash_is_order_sensitive() -> None:
    assert row_ids_sha256(["a", "b"]) != row_ids_sha256(["b", "a"])
