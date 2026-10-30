"""Source-only original-state tests. Never load models or execute treatments."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.stage10.stage10a_original_state_preflight import (
    json_core_hash,
    normalized_rule_text_hash,
    verify_checkpoints,
    verify_r0_rules,
)


def _checkpoints(tmp_path):
    expected = {}
    for seed in range(5):
        content = f"synthetic-seed-{seed}".encode()
        (tmp_path / f"seed_{seed}.pt").write_bytes(content)
        expected[str(seed)] = hashlib.sha256(content).hexdigest()
    return expected


def _rules(tmp_path):
    rules = []
    for seed in range(5):
        rel = f"data/rules/system_b_r0_v2/seed_{seed}.json"
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        core = {"seed": seed, "symbolic_rule": f"synthetic-{seed}"}
        digest = json_core_hash(core)
        payload = {**core, "artifact_sha256": digest}
        p.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        rules.append({
            "seed": seed, "path": rel,
            "text_sha256": normalized_rule_text_hash(p),
            "artifact_sha256": digest,
        })
    return rules


def test_five_seed_source_only_checkpoint_sha256(tmp_path) -> None:
    expected = _checkpoints(tmp_path)
    assert len(verify_checkpoints(tmp_path, expected)) == 5


def test_corrupted_or_missing_checkpoint_fails_closed(tmp_path) -> None:
    expected = _checkpoints(tmp_path)
    (tmp_path / "seed_3.pt").write_bytes(b"modified")
    with pytest.raises(ValueError, match="seed 3 SHA-256 mismatch"):
        verify_checkpoints(tmp_path, expected)
    (tmp_path / "seed_3.pt").unlink()
    with pytest.raises(ValueError, match="seed 3 file unavailable"):
        verify_checkpoints(tmp_path, expected)


def test_missing_or_added_checkpoint_seed_is_not_silent(tmp_path) -> None:
    expected = _checkpoints(tmp_path)
    expected.pop("4")
    with pytest.raises(ValueError, match="exact five"):
        verify_checkpoints(tmp_path, expected)


def test_five_seed_symbolic_rule_dual_hash_identity(tmp_path) -> None:
    rules = _rules(tmp_path)
    assert len(verify_r0_rules(tmp_path, rules)) == 5


def test_crlf_portability_preserves_accepted_lf_text_hash(tmp_path) -> None:
    rules = _rules(tmp_path)
    target = tmp_path / rules[0]["path"]
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    assert len(verify_r0_rules(tmp_path, rules)) == 5


def test_r0_semantic_tamper_and_raw_text_tamper_rejected(tmp_path) -> None:
    rules = _rules(tmp_path)
    p = tmp_path / rules[0]["path"]
    modified = json.loads(p.read_text(encoding="utf-8"))
    modified["seed"] = 42
    p.write_text(json.dumps(modified, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="text/artifact identity mismatch"):
        verify_r0_rules(tmp_path, rules)


def test_mismatched_r0_path_and_count_fail_closed(tmp_path) -> None:
    rules = _rules(tmp_path)
    rules[0]["path"] = "../unexpected.json"
    with pytest.raises(ValueError, match="path differs"):
        verify_r0_rules(tmp_path, rules)
    with pytest.raises(ValueError, match="exactly the five"):
        verify_r0_rules(tmp_path, rules[:4])


def test_exact_five_committed_r0_rule_identities_against_frozen_assurance_inventory() -> None:
    """Actual repository R0 rules, not mock models or outcome-bearing data."""
    root = Path(__file__).resolve().parents[2]
    audit = json.loads(
        (root / "data/manifests/stage9_5_fresh_clone_reconstruction_v1_2.json")
        .read_text(encoding="utf-8")
    )
    assert audit["r0_v2"]["manifest_sha256"] == (
        "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483"
    )
    records = verify_r0_rules(root, audit["r0_v2"]["rules"])
    assert tuple(item["seed"] for item in records) == tuple(range(5))
    for observed, frozen in zip(records, audit["r0_v2"]["rules"], strict=True):
        assert observed["normalized_text_sha256"] == frozen["text_sha256"]
        assert observed["artifact_sha256"] == frozen["artifact_sha256"]
