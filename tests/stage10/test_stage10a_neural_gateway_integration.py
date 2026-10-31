"""Integration tests for the REAL shared runner's optional label-free path.

Synthetic minimal model parameters only. No original source/checkpoint, no
Stage-10A neural treatment, no outcome metrics, no execution authorization.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

from concept_drift_ids.cd_shared_runner import AnchorRow, ControlPlaneConfig, StreamRow
from concept_drift_ids.stage10a_control_runner import (
    Stage10AControlPlaneRunner, Stage10ALabelGrant, UnlabeledStreamRow,
)
from concept_drift_ids.neural import BinaryMLP
from concept_drift_ids.stage10a_neural_input import SealedStage10AFeatureRows


def _runner(tmp_path):
    model = BinaryMLP(input_features=77, hidden_layers=(2,), dropout=0.0)
    # This synthetic one-anchor budget is for a no-update interface test only.
    config = ControlPlaneConfig(replay_anchor_rows=1, replay_online_rows=0)
    return Stage10AControlPlaneRunner(
        seed=0, initial_model=model, initial_checkpoint_sha256="a" * 64,
        monitor_threshold=0.5, anchor_rows=[
            AnchorRow("historical-anchor", np.zeros(77, dtype=np.float32), 0)
        ], checkpoint_dir=tmp_path / "test-only-checkpoints",
        run_id="gate-interface-test-only", git_commit="b" * 40,
        config=config,
    )


class _GrantStub:
    def __init__(self, *, premature=False, omit=False):
        self.calls = []
        self.premature = premature
        self.omit = omit

    def commit_prediction(self, **kwargs):
        assert "true_label" not in kwargs
        assert "boundary_index" not in kwargs
        self.calls.append(kwargs)
        index = kwargs["origin_index"]
        if self.premature:
            return Stage10ALabelGrant(index, 1)
        if index < 5000 or self.omit:
            return None
        return Stage10ALabelGrant(index - 5000, 1)


def _rows(n):
    x = np.zeros(77, dtype=np.float32)
    return [UnlabeledStreamRow(f"r{i}", x) for i in range(n)]


def test_label_free_real_runner_path_releases_only_after_commit(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    monkeypatch.setattr(runner, "_predict_one", lambda model, features: 0.25)
    gate = _GrantStub()
    result = runner.run(_rows(5001), label_gateway=gate)
    assert len(gate.calls) == 5001
    assert gate.calls[0]["origin_index"] == 0
    assert gate.calls[5000]["maturity_index"] == 10000
    assert result.pending_labels == 5000
    assert len(result.predictions) == 5001
    assert len(result.detector_observations) == 1
    releases = [x for x in result.events if x["event_type"] == "label_release"]
    assert len(releases) == 1
    assert releases[0]["origin_index"] == 0


def test_gateway_refuses_labeled_input_before_model_call(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    monkeypatch.setattr(runner, "_predict_one", lambda *a: pytest.fail("model called"))
    with pytest.raises(ValueError, match="label-free"):
        runner.run([StreamRow("r0", np.zeros(77), 1)], label_gateway=_GrantStub())


def test_gateway_refuses_premature_label_and_no_label_after_maturity(tmp_path, monkeypatch):
    runner = _runner(tmp_path)
    monkeypatch.setattr(runner, "_predict_one", lambda *a: 0.25)
    with pytest.raises(ValueError, match="before maturity"):
        runner.run(_rows(1), label_gateway=_GrantStub(premature=True))
    with pytest.raises(ValueError, match="missing, early or forged"):
        runner.run(_rows(5001), label_gateway=_GrantStub(omit=True))


def test_feature_reader_rejects_non_frozen_tensor(tmp_path):
    f = tmp_path / "test-features.npy"
    np.save(f, np.zeros((2, 77), dtype=np.float32), allow_pickle=False)
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Unexpected frozen"):
        SealedStage10AFeatureRows(f, expected_sha256=sha)
    with pytest.raises(ValueError, match="byte hash"):
        SealedStage10AFeatureRows(f, expected_sha256="0" * 64)
    link = tmp_path / "bad-symlink.npy"
    link.symlink_to(f)
    with pytest.raises(ValueError, match="Symlink"):
        SealedStage10AFeatureRows(link, expected_sha256=sha)
