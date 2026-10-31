"""Repository-only frozen receipt checks. No .pt, models, data, or treatments."""
from __future__ import annotations

import copy
import inspect
import json

import pytest
import tools.stage10.stage10a_pre_release_evidence_gate as gate


def test_current_accepted_source_only_artifacts_are_not_a_release():
    report = gate.assess()
    assert report["source_receipt_verified"] is True
    assert report["original_checkpoint_receipt_verified"] is True
    assert report["original_checkpoint_seeds_verified"] == 5
    assert report["r0_rule_seeds_verified"] == 5
    for key in (
        "matched_three_arm_neural_execution_verified",
        "prediction_before_label_runtime_verified",
        "independent_environment_experiment_verified",
        "stage10a_treatment_execution_authorized", "stage10a_release_ready",
    ):
        assert report[key] is False
    assert report["status"].startswith("HOLD_")


@pytest.mark.parametrize("path,change,match", [
    (gate.MASTER_PATH, lambda x: x["hard_gate"].update(stage10_execution_permitted=True), "HOLD"),
    (gate.STAGE_PATH, lambda x: x.update(stage10_treatment_execution_authorized=True), "HOLD"),
    (gate.CANDIDATE_PATH, lambda x: x["governance"].update(release_signed=True), "HOLD"),
    (gate.SOURCE_PATH, lambda x: x.update(logical_rows=138529), "source-only receipt"),
    (gate.SOURCE_PATH, lambda x: x.update(model_checkpoints_loaded=True), "source-only receipt"),
    (gate.CHECKPOINT_PATH, lambda x: x["checkpoint_files"][3].update(sha256="0" * 64), "checkpoint seeds"),
    (gate.CHECKPOINT_PATH, lambda x: x["r0_rule_files"][2].update(artifact_sha256="0" * 64), "symbolic R0"),
    (gate.CHECKPOINT_PATH, lambda x: x.update(checkpoint_bytes_preserved_in_artifact=True), "identity invalid"),
    (gate.CHECKPOINT_PATH, lambda x: x.update(no_model_loaded_or_predicted=False), "identity invalid"),
    (gate.CHECKPOINT_PATH, lambda x: x.update(stage10a_treatment_execution_authorized=True), "HOLD"),
    (gate.INVENTORY_PATH, lambda x: x["system_a"]["checkpoints"][0].update(sha256="0" * 64), "identities diverge"),
    (gate.INVENTORY_PATH, lambda x: x["r0_v2"]["rules"][4].update(text_sha256="0" * 64), "symbolic R0"),
])
def test_tampered_frozen_identity_or_release_flags_fail_closed(monkeypatch, path, change, match):
    original = gate._read_json
    def substituted(root, relative, **kwargs):
        result = original(root, relative, **kwargs)
        if relative == path:
            result = copy.deepcopy(result)
            change(result)
        return result
    monkeypatch.setattr(gate, "_read_json", substituted)
    with pytest.raises(ValueError, match=match):
        gate.assess()


def test_unaccepted_raw_receipt_bytes_rejected_before_parsing(tmp_path):
    path = tmp_path / gate.CHECKPOINT_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"pass": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unaccepted bytes"):
        gate._read_json(tmp_path, gate.CHECKPOINT_PATH, raw_sha=gate.CHECKPOINT_RAW_SHA256)


def test_no_treatment_imports_or_side_effecting_writers():
    source = inspect.getsource(gate)
    for prohibited in ("torch.load(", "pickle.load(", "model.predict(",
                       ".write_bytes(", ".write_text(", "requests.get(", "urlopen("):
        assert prohibited not in source
