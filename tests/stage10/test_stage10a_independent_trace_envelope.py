"""Independent source-only schema tests; never load models or raw CICIDS."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from tools.stage10 import stage10a_independent_trace_envelope as audit
from tools.stage10.stage10a_shared_writer_synthetic import (
    ARMS, SEEDS, write_shared_fixture, bind_readonly_arm,
)


@pytest.fixture(autouse=True)
def no_hardware_fsync(monkeypatch):
    # Existing fixture writer still calls fsync per event, with no host disk cost.
    monkeypatch.setattr("tools.stage10.stage10a_shared_writer_synthetic.os.fsync",
                        lambda _fd: None)


def _json_bytes(document):
    return (json.dumps(document, sort_keys=True, separators=(",", ":"),
                       allow_nan=False, ensure_ascii=False) + "\n").encode()


def _construct(root: Path, seeds=(0,), count=audit.LOW):
    stage, original = audit.read_authorities()
    for seed in seeds:
        write_shared_fixture(root, seed=seed, count=count)
        for arm in ARMS:
            bind_readonly_arm(root, seed=seed, arm=arm, count=count)
        d = root / f"seed-{seed}"
        files = {name: hashlib.sha256((d / name).read_bytes()).hexdigest()
                 for name in audit.ARTIFACT_FILES}
        envelope = audit.expected_envelope(seed, count, files, stage, original)
        (d / "trace_envelope.json").write_bytes(_json_bytes(envelope))


def _overwrite(path, update):
    data = json.loads(path.read_bytes())
    update(data)
    path.write_bytes(_json_bytes(data))


def test_all_five_original_seed_identity_bindings_without_treatment(tmp_path):
    _construct(tmp_path, SEEDS)
    result = audit.audit_all(tmp_path)
    assert result["five_seed_envelopes_valid"] is True
    assert result["accepted_source_only_receipts_rechecked"] is True
    assert len(set(result["shared_raw_journal_sha256_by_seed"].values())) == 5
    for flag in ("production_git_head_authenticated",
                 "production_neural_checkpoint_chain_verified",
                 "production_prediction_label_order_verified",
                 "real_matched_three_arm_neural_execution_verified",
                 "model_loaded_or_predicted",
                 "stage10a_treatment_execution_authorized", "stage10a_release_ready"):
        assert result[flag] is False


@pytest.mark.parametrize("mutation", [
    "wrong_original_checkpoint", "wrong_original_source", "wrong_preprocessor",
    "alter_r0", "release_flag", "unverified_runtime_claim", "arm_injected",
])
def test_envelope_cannot_launder_invalid_identity(tmp_path, mutation):
    _construct(tmp_path)
    path = tmp_path / "seed-0/trace_envelope.json"
    def change(doc):
        if mutation == "wrong_original_checkpoint":
            doc["initial_checkpoint_sha256"] = "0" * 64
        elif mutation == "wrong_original_source":
            doc["source_sha256"] = "1" * 64
        elif mutation == "wrong_preprocessor":
            doc["preprocessing_core_sha256"] = "2" * 64
        elif mutation == "alter_r0":
            doc["r0_v2_manifest_sha256"] = "3" * 64
        elif mutation == "release_flag":
            doc["stage10a_treatment_execution_authorized"] = True
        elif mutation == "unverified_runtime_claim":
            doc["git_head_independently_authenticated"] = True
        else:
            doc["arms"].append("new_posthoc_comparator")
    _overwrite(path, change)
    stage, original = audit.read_authorities()
    with pytest.raises(ValueError, match="Envelope"):
        audit.audit_seed(tmp_path, 0, audit.LOW, stage, original)


@pytest.mark.parametrize("mutation", [
    "prediction_truth", "boundary_leak", "early_label",
    "order_swap", "forged_neural_token", "forged_seal",
    "cross_seed_arm", "second_writer", "missing_event",
])
def test_forged_digest_cannot_hide_raw_evidence_tampering(tmp_path, mutation):
    _construct(tmp_path)
    d = tmp_path / "seed-0"
    journal = d / "shared.jsonl"
    if mutation in {"prediction_truth", "boundary_leak", "early_label",
                    "order_swap", "forged_neural_token", "missing_event"}:
        lines = journal.read_bytes().splitlines(keepends=True)
        if mutation in {"prediction_truth", "boundary_leak", "forged_neural_token"}:
            first = json.loads(lines[0])
            if mutation == "prediction_truth":
                first["true_label"] = 1
            elif mutation == "boundary_leak":
                first["boundary_index"] = 69260
            else:
                first["synthetic_neural_token_sha256"] = "0" * 64
            lines[0] = _json_bytes(first)
        elif mutation == "early_label":
            lines[0] = _json_bytes({"event_type": "label_release",
                                     "origin_index": 0, "maturity_index": 0,
                                     "logical_clock": 0})
        elif mutation == "order_swap":
            lines[0], lines[1] = lines[1], lines[0]
        else:
            lines.pop()
        journal.write_bytes(b"".join(lines))
    elif mutation == "forged_seal":
        _overwrite(d / "sealed.json", lambda x: x.update(journal_sha256="0" * 64))
    elif mutation == "cross_seed_arm":
        _overwrite(d / f"arm-{ARMS[1]}.json", lambda x: x.update(seed=1))
    else:
        _overwrite(d / f"arm-{ARMS[0]}.json",
                   lambda x: x.update(neural_writer_invocations=2))
    # Attacker even refreshes the envelope's raw SHA strings; trace invariants
    # and frozen identities MUST independently refuse the forged data.
    envelope_path = d / "trace_envelope.json"
    _overwrite(envelope_path, lambda x: x.update(artifacts_sha256={
        name: hashlib.sha256((d / name).read_bytes()).hexdigest()
        for name in audit.ARTIFACT_FILES
    }))
    stage, original = audit.read_authorities()
    with pytest.raises(ValueError, match="Prediction|Premature|missing|Sealed|Arm|raw event|changed|reordered|leaked"):
        audit.audit_seed(tmp_path, 0, audit.LOW, stage, original)


def test_missing_or_unexpected_artifact_is_hard_failure(tmp_path):
    _construct(tmp_path)
    d = tmp_path / "seed-0"
    (d / "unexpected-model.pt").write_bytes(b"not a model")
    stage, original = audit.read_authorities()
    with pytest.raises(ValueError, match="Unexpected"):
        audit.audit_seed(tmp_path, 0, audit.LOW, stage, original)


def test_symbolic_arm_references_raw_shared_seal_not_just_claims(tmp_path):
    _construct(tmp_path)
    d = tmp_path / "seed-0"
    p = d / f"arm-{ARMS[-1]}.json"
    _overwrite(p, lambda x: x.update(shared_seal_sha256="c" * 64))
    env = d / "trace_envelope.json"
    _overwrite(env, lambda x: x.update(artifacts_sha256={
        name: hashlib.sha256((d / name).read_bytes()).hexdigest()
        for name in audit.ARTIFACT_FILES
    }))
    stage, original = audit.read_authorities()
    with pytest.raises(ValueError, match="Arm"):
        audit.audit_seed(tmp_path, 0, audit.LOW, stage, original)


def test_frozen_authority_not_replaceable_with_simulated_release(monkeypatch):
    read = audit._frozen_json
    def changed(root, path, sha, *, git_blob=False):
        data = read(root, path, sha, git_blob=git_blob)
        if path.endswith("stage10a_goldeneye_attack_pattern_v1.json"):
            data = copy.deepcopy(data)
            data["stage10_treatment_execution_authorized"] = True
        return data
    monkeypatch.setattr(audit, "_frozen_json", changed)
    with pytest.raises(ValueError, match="HOLD"):
        audit.read_authorities()


def test_real_row_count_never_accepted_as_synthetic(tmp_path):
    stage, original = audit.read_authorities()
    with pytest.raises(ValueError, match="synthetic"):
        audit.expected_envelope(0, 138530, {}, stage, original)
    with pytest.raises(ValueError, match="non-synthetic"):
        audit.audit_seed(tmp_path, 0, 138530, stage, original)


def test_missing_seed_fails_even_if_four_are_valid(tmp_path):
    _construct(tmp_path, (0, 1, 2, 3))
    with pytest.raises(ValueError, match="five disjoint"):
        audit.audit_all(tmp_path)


def test_no_writer_dependency_no_treatment_api_no_network():
    source = inspect.getsource(audit)
    for forbidden in ("stage10a_shared_writer_synthetic", "torch.load(",
                      "pickle.load(", "model.predict(", "requests.get(",
                      "urlopen(", ".write_bytes(", "open(\"x\""):
        assert forbidden not in source
