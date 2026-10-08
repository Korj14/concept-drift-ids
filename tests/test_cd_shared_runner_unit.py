from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest
import torch

from concept_drift_ids.cd_control_plane import (
    NeuralUpdateConfig,
    SharedErrorDriftMonitor,
)
from concept_drift_ids.cd_shared_runner import (
    AnchorRow,
    ControlPlaneConfig,
    SharedControlPlaneRunner,
    StreamRow,
    freeze_shared_trajectory,
    verify_primary_control_plane_configuration,
    verify_shared_trajectory,
)
from concept_drift_ids.neural import BinaryMLP


class _FakeADWIN:
    def __init__(self) -> None:
        self.count = 0
        self.drift_detected = False

    def update(self, _: int) -> None:
        self.count += 1
        self.drift_detected = self.count >= 2


def _rows(prefix: str, count: int) -> list[StreamRow]:
    rows: list[StreamRow] = []
    for i in range(count):
        label = i % 2
        base = float(label)
        rows.append(
            StreamRow(
                row_id=f"{prefix}-{i}",
                features=np.array(
                    [base, base + 0.1, base + 0.2],
                    dtype=np.float32,
                ),
                label=label,
            )
        )
    return rows


def _anchors(count: int) -> list[AnchorRow]:
    rows: list[AnchorRow] = []
    for i in range(count):
        label = i % 2
        base = float(label)
        rows.append(
            AnchorRow(
                row_id=f"anchor-{i}",
                features=np.array(
                    [base + 0.3, base + 0.4, base + 0.5],
                    dtype=np.float32,
                ),
                label=label,
            )
        )
    return rows


def _config() -> ControlPlaneConfig:
    return ControlPlaneConfig(
        label_latency=1,
        current_window=4,
        reservoir_capacity=4,
        replay_anchor_rows=2,
        replay_online_rows=2,
        neural_update=NeuralUpdateConfig(
            learning_rate=1e-3,
            weight_decay=0.0,
            batch_size=4,
            epochs=1,
            pos_weight=1.0,
        ),
    )


def test_runner_publishes_shared_child_and_quarantines_stale_errors(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SharedErrorDriftMonitor,
        "_new_adwin",
        staticmethod(lambda: _FakeADWIN()),
    )
    torch.manual_seed(11)
    model = BinaryMLP(input_features=3, hidden_layers=(4, 2), dropout=0.1)
    runner = SharedControlPlaneRunner(
        seed=0,
        initial_model=model,
        initial_checkpoint_sha256="initial-file-sha",
        monitor_threshold=0.5,
        anchor_rows=_anchors(4),
        checkpoint_dir=tmp_path / "checkpoints",
        run_id="toy-run",
        git_commit="deadbeef",
        config=_config(),
    )

    trajectory = runner.run(_rows("stream", 9))

    assert len(trajectory.predictions) == 9
    assert len(trajectory.label_schedule) == 9
    assert len(trajectory.checkpoint_chain) >= 2
    assert trajectory.final_checkpoint_sha256 != "initial-file-sha"
    assert trajectory.pending_labels == 1

    reasons = [item["reason"] for item in trajectory.detector_observations]
    assert "stale_checkpoint_error" in reasons

    publications = [
        event
        for event in trajectory.events
        if event["event_type"] == "neural_publication"
    ]
    assert publications
    assert publications[0]["payload"]["publication_effective_index"] > (
        publications[0]["logical_clock"]
    )

    first_transaction = trajectory.replay_transactions[0]
    assert not set(first_transaction["current_row_ids"]).intersection(
        first_transaction["replay_row_ids"]
    )

    verify_shared_trajectory(trajectory, label_latency=1)


def test_runner_is_deterministic_at_state_level_for_same_inputs(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SharedErrorDriftMonitor,
        "_new_adwin",
        staticmethod(lambda: _FakeADWIN()),
    )
    torch.manual_seed(17)
    parent = BinaryMLP(input_features=3, hidden_layers=(4, 2), dropout=0.1)

    left = SharedControlPlaneRunner(
        seed=1,
        initial_model=parent,
        initial_checkpoint_sha256="initial-file-sha",
        monitor_threshold=0.5,
        anchor_rows=_anchors(4),
        checkpoint_dir=tmp_path / "left",
        run_id="toy-run-left",
        git_commit="deadbeef",
        config=_config(),
    ).run(_rows("stream", 9))

    right = SharedControlPlaneRunner(
        seed=1,
        initial_model=parent,
        initial_checkpoint_sha256="initial-file-sha",
        monitor_threshold=0.5,
        anchor_rows=_anchors(4),
        checkpoint_dir=tmp_path / "right",
        run_id="toy-run-right",
        git_commit="deadbeef",
        config=_config(),
    ).run(_rows("stream", 9))

    assert left.final_state_sha256 == right.final_state_sha256
    assert [
        item["child_state_sha256"] for item in left.checkpoint_chain
    ] == [
        item["child_state_sha256"] for item in right.checkpoint_chain
    ]


def test_freeze_shared_trajectory_is_non_overwriting(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SharedErrorDriftMonitor,
        "_new_adwin",
        staticmethod(lambda: _FakeADWIN()),
    )
    torch.manual_seed(19)
    model = BinaryMLP(input_features=3, hidden_layers=(4, 2), dropout=0.1)
    trajectory = SharedControlPlaneRunner(
        seed=2,
        initial_model=model,
        initial_checkpoint_sha256="initial-file-sha",
        monitor_threshold=0.5,
        anchor_rows=_anchors(4),
        checkpoint_dir=tmp_path / "checkpoints",
        run_id="toy-run",
        git_commit="deadbeef",
        config=_config(),
    ).run(_rows("stream", 9))

    output = tmp_path / "frozen"
    files = freeze_shared_trajectory(output, trajectory)
    assert {
        "predictions",
        "label_schedule",
        "detector_observations",
        "events",
        "replay_transactions",
        "checkpoint_chain",
        "shared_identity",
    } == set(files)

    identity = json.loads(
        (output / "shared_identity.json").read_text(encoding="utf-8")
    )
    assert identity["shared_identity"]["identity_sha256"] == (
        trajectory.shared_identity["identity_sha256"]
    )

    with pytest.raises(FileExistsError, match="overwrite"):
        freeze_shared_trajectory(output, trajectory)


def test_runner_rejects_anchor_stream_identity_collision(tmp_path) -> None:
    torch.manual_seed(23)
    model = BinaryMLP(input_features=3, hidden_layers=(4, 2), dropout=0.1)
    anchors = _anchors(4)
    collision = [
        StreamRow(
            row_id="anchor-0",
            features=np.zeros(3, dtype=np.float32),
            label=0,
        )
    ]
    runner = SharedControlPlaneRunner(
        seed=0,
        initial_model=model,
        initial_checkpoint_sha256="initial",
        monitor_threshold=0.5,
        anchor_rows=anchors,
        checkpoint_dir=tmp_path / "checkpoints",
        run_id="toy",
        git_commit="deadbeef",
        config=_config(),
    )
    with pytest.raises(ValueError, match="disjoint"):
        runner.run(collision)



def test_shared_trajectory_verifier_rejects_maturity_tampering(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SharedErrorDriftMonitor,
        "_new_adwin",
        staticmethod(lambda: _FakeADWIN()),
    )
    torch.manual_seed(29)
    model = BinaryMLP(input_features=3, hidden_layers=(4, 2), dropout=0.1)
    trajectory = SharedControlPlaneRunner(
        seed=3,
        initial_model=model,
        initial_checkpoint_sha256="initial-file-sha",
        monitor_threshold=0.5,
        anchor_rows=_anchors(4),
        checkpoint_dir=tmp_path / "checkpoints",
        run_id="toy-run",
        git_commit="deadbeef",
        config=_config(),
    ).run(_rows("stream", 6))

    tampered_schedule = list(trajectory.label_schedule)
    tampered_schedule[0] = dict(
        tampered_schedule[0],
        maturity_index=99,
    )
    tampered = replace(
        trajectory,
        label_schedule=tuple(tampered_schedule),
    )
    with pytest.raises(ValueError, match="maturity"):
        verify_shared_trajectory(tampered, label_latency=1)



def test_shared_runner_has_no_primary_scenario_loader_surface() -> None:
    import concept_drift_ids.cd_shared_runner as module

    source = module.__file__
    assert source is not None
    text = open(source, encoding="utf-8").read()
    assert "scenario_loader" not in text
    assert "load_partition" not in text
    assert "pre_drift" not in text
    assert "post_drift" not in text



def test_primary_configuration_verifier_rejects_toy_overrides() -> None:
    from concept_drift_ids.cd_control_plane import (
        PRIMARY_ANCHOR_CAPACITY,
        SYSTEM_A_MONITOR_THRESHOLDS,
    )

    verify_primary_control_plane_configuration(
        seed=0,
        monitor_threshold=SYSTEM_A_MONITOR_THRESHOLDS[0],
        anchor_row_count=PRIMARY_ANCHOR_CAPACITY,
        config=ControlPlaneConfig(),
    )

    with pytest.raises(ValueError, match="frozen defaults"):
        verify_primary_control_plane_configuration(
            seed=0,
            monitor_threshold=SYSTEM_A_MONITOR_THRESHOLDS[0],
            anchor_row_count=PRIMARY_ANCHOR_CAPACITY,
            config=_config(),
        )
