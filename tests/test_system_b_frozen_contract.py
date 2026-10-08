from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "manifests" / "system_b_v1.json"
SYSTEM_A_MANIFEST_PATH = ROOT / "data" / "manifests" / "system_a_v1.json"

EXPECTED_MANIFEST_HASH = (
    "6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8"
)


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_committed_system_b_r0_contract_is_self_consistent() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored_manifest_hash = manifest["manifest_sha256"]
    manifest_core = dict(manifest)
    manifest_core.pop("manifest_sha256")

    assert stored_manifest_hash == EXPECTED_MANIFEST_HASH
    assert _canonical_hash(manifest_core) == stored_manifest_hash
    assert manifest["system_id"] == "system_b_static_neuro_symbolic_v1"
    assert manifest["rule_base_version"] == "R0.v1"
    assert manifest["preprocessing_state_hash"] == (
        "4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e"
    )
    assert manifest["system_a_manifest_sha256"] == (
        "42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de"
    )
    assert manifest["data_access"] == {
        "training_used": True,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }
    assert manifest["config"]["backend"] == "cpu"
    assert manifest["fusion"]["selected_neural_weight"] == 0.5

    system_a = json.loads(SYSTEM_A_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert system_a["manifest_sha256"] == manifest["system_a_manifest_sha256"]
    a_records = {int(row["seed"]): row for row in system_a["seed_records"]}

    expected_active_counts = {0: 7, 1: 8, 2: 7, 3: 8, 4: 6}
    expected_thresholds = {
        0: 0.692427396774292,
        1: 0.9235901534557343,
        2: 0.8299936652183533,
        3: 0.9747405052185059,
        4: 0.9527904391288757,
    }

    observed_ids: set[str] = set()

    for seed in range(5):
        entry = manifest["rule_artifacts"][str(seed)]
        rule_path = ROOT / entry["path"]
        assert rule_path.is_file()
        assert _file_hash(rule_path) == entry["sha256"]

        artifact = json.loads(rule_path.read_text(encoding="utf-8"))
        stored_artifact_hash = artifact["artifact_sha256"]
        artifact_core = dict(artifact)
        artifact_core.pop("artifact_sha256")

        assert _canonical_hash(artifact_core) == stored_artifact_hash
        assert stored_artifact_hash == entry["artifact_sha256"]
        assert artifact["seed"] == seed
        assert artifact["rule_base_version"] == "R0.v1"
        assert artifact["system_a_checkpoint_sha256"] == (
            a_records[seed]["checkpoint_sha256"]
        )
        assert artifact["system_a_threshold"] == a_records[seed]["threshold"]
        assert len(artifact["selected_features"]) == 12

        candidate_log = artifact["candidate_log"]
        accepted_candidates = {
            row["rule_id"]
            for row in candidate_log
            if row["accepted_by_quality_gate"]
        }
        rules = artifact["rules"]
        assert len(rules) == expected_active_counts[seed]
        assert len(rules) == entry["active_rule_count"]
        assert {
            rule["rule_id"] for rule in rules
        }.issubset(accepted_candidates)

        for rule in rules:
            assert rule["rule_id"] not in observed_ids
            observed_ids.add(rule["rule_id"])
            assert rule["lifecycle_state"] == "active"
            assert rule["support"] >= 0.001
            assert rule["covered_count"] >= 100
            assert rule["class_precision"] >= 0.80
            assert rule["neural_fidelity"] >= 0.90
            assert rule["stability"] >= 0.90
            assert rule["complexity"] <= 4

        assert manifest["fusion"]["per_seed_thresholds"][str(seed)] == (
            expected_thresholds[seed]
        )

    assert len(observed_ids) == sum(expected_active_counts.values())
