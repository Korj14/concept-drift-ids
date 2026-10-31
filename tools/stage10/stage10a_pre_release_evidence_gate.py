"""Read-only Stage-10A source-identity acceptance guard; NOT a RELEASE.

Verify original-source and checkpoint/R0 receipts against frozen authorities.
Does not access raw dataset, .pt, model, network, treatment results, or outcomes.
An accepted receipt does NOT establish real matched C/D/D-periodic execution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = "results/audits/stage10a_original_source_receipt_601516ff_2026_10_31.json"
CHECKPOINT_PATH = "results/audits/stage10a_original_checkpoint_source_only_receipt_41156553037.json"
MASTER_PATH = "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json"
STAGE_PATH = "data/manifests/stage10a_goldeneye_attack_pattern_v1.json"
PRIMARY_PATH = "data/manifests/cd_primary_run_config_v1_1.json"
CANDIDATE_PATH = "data/manifests/stage10a_execution_candidate_v1.json"
INVENTORY_PATH = "data/manifests/stage9_5_fresh_clone_reconstruction_v1_2.json"

SOURCE_RAW_SHA256 = "d6e0874181b4aebe4d259b7f4f66b7d608aaf7803c6dc3c10f0151aaf2f9a42a"
CHECKPOINT_RAW_SHA256 = "94cf6ee608e63be4834372aa0be8956eaaf289234f395dd788a9e0d23ba2b1c1"
SOURCE_BLOB_SHA1 = "a3f2e1e9cec47add542505cab2e48eec2c4351ad"
MASTER_BLOB_SHA1 = "8ac82c8d907243556a5673d09600cd1bdc19aa52"
STAGE_BLOB_SHA1 = "001501350fbf9fa4a4075176b9af43c2cf275bc5"
SOURCE_CORE_SHA256 = "eb145dda1654df375016eb254e90e469b3318ebbc7a6fd17b4402a9ef855c93a"
SOURCE_RUN_SHA = "601516ff7e71d14fdcab2c7caa76fdc512aa9e71"
CHECKPOINT_RUN_SHA = "b9df68e796a92e17ebc171b87ae7217942150a7b"


def _read_json(root: Path, path: str, *, raw_sha: str | None = None,
               git_blob: str | None = None) -> dict[str, Any]:
    raw = (root / path).read_bytes()
    if raw_sha is not None and hashlib.sha256(raw).hexdigest() != raw_sha:
        raise ValueError(f"Unaccepted bytes at {path}")
    if git_blob is not None:
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if actual != git_blob:
            raise ValueError(f"Frozen Git blob changed at {path}")
    item = json.loads(raw)
    if not isinstance(item, dict):
        raise ValueError(f"Invalid document at {path}")
    return item


def _same_false(obj: dict[str, Any], *keys: str) -> None:
    if any(obj.get(key) is not False for key in keys):
        raise ValueError("Scientific treatment/outcome HOLD changed")


def assess(root: Path = ROOT) -> dict[str, Any]:
    """Independently check preserved source-only evidence; retain HOLD."""
    master = _read_json(root, MASTER_PATH, git_blob=MASTER_BLOB_SHA1)
    stage = _read_json(root, STAGE_PATH, git_blob=STAGE_BLOB_SHA1)
    candidate = _read_json(root, CANDIDATE_PATH)
    primary = _read_json(root, PRIMARY_PATH)
    inventory = _read_json(root, INVENTORY_PATH)
    source = _read_json(root, SOURCE_PATH, raw_sha=SOURCE_RAW_SHA256,
                        git_blob=SOURCE_BLOB_SHA1)
    checkpoints = _read_json(root, CHECKPOINT_PATH, raw_sha=CHECKPOINT_RAW_SHA256)

    _same_false(master["hard_gate"], "stage10_execution_permitted")
    _same_false(master, "stage10_treatment_outcomes_accessed")
    _same_false(stage, "stage10_treatment_execution_authorized",
                "stage10_treatment_outcomes_accessed_during_freeze")
    _same_false(candidate["governance"], "stage10_execution_permitted",
                "stage10a_treatment_execution_authorized", "release_signed")
    if (len(master["stage_specific_pre_outcome_freeze_required"]) != 19
        or len(master["master_obligations"]) != 16
        or tuple(stage["inherited_identities"]["seeds"]) != (0, 1, 2, 3, 4)
        or tuple(stage["primary_arms"]) !=
            ("c_frozen_symbolic", "d_drift", "d_periodic")):
        raise ValueError("Frozen stage structure changed")

    if (source.get("pass") is not True or
        source.get("audit_id") != "stage10a-original-source-receipt-v1" or
        source.get("canonical_sha256") != SOURCE_CORE_SHA256 or
        source.get("git") != {"branch": "stage10a-governance",
                              "clean": "true", "head": SOURCE_RUN_SHA} or
        source.get("python_version") != "3.11.9" or
        source.get("frozen_features") != 77 or
        source.get("logical_rows") != 138530 or
        source.get("label_latency_rows") != 5000 or
        source.get("raw_source_sha256") != stage["raw_source"]["sha256"] or
        source.get("ordered_row_ids_sha256") != stage["scenario"]["stream_row_ids_sha256"] or
        source.get("model_checkpoints_loaded") is not False or
        source.get("neural_or_symbolic_treatments_executed") is not False):
        raise ValueError("Accepted source-only receipt contradicts frozen source")
    _same_false(source, "stage10_treatment_execution_authorized",
                "stage10_treatment_outcomes_accessed")

    if (checkpoints.get("pass") is not True or
        checkpoints.get("audit_id") != "stage10a-original-checkpoint-source-only-github-transfer-v1" or
        checkpoints.get("status") != "original_artifact_bytes_verified_but_not_treatment_release" or
        checkpoints.get("git_head") != CHECKPOINT_RUN_SHA or
        checkpoints.get("git_branch") != "stage10a-governance" or
        checkpoints.get("python_version") != "3.11.9" or
        checkpoints.get("original_checkpoint_bytes_transferred_ephemerally") is not True or
        checkpoints.get("checkpoint_bytes_preserved_in_artifact") is not False or
        checkpoints.get("dropbox_links_preserved_in_artifact") is not False or
        checkpoints.get("no_model_loaded_or_predicted") is not True or
        checkpoints.get("source_receipt_canonical_complete") is not True or
        checkpoints.get("source_receipt_canonical_sha256") != SOURCE_CORE_SHA256 or
        checkpoints.get("source_receipt_git_blob_sha1") != SOURCE_BLOB_SHA1):
        raise ValueError("Accepted original-checkpoint receipt identity invalid")
    _same_false(checkpoints, "stage10a_treatment_execution_authorized",
                "stage10_treatment_outcomes_accessed")

    source_expected = inventory["system_a"]["checkpoints"]
    frozen_seed_map = {str(item["seed"]): item["sha256"] for item in source_expected}
    if (len(source_expected) != 5 or set(frozen_seed_map) != set("01234") or
        candidate["inherited_neural"]["checkpoint_sha256_by_seed"] != frozen_seed_map or
        primary["system_a"]["checkpoint_sha256_by_seed"] != frozen_seed_map):
        raise ValueError("Inherited original-checkpoint identities diverge")
    observed = checkpoints.get("checkpoint_files")
    if (type(observed) is not list or len(observed) != 5 or
        observed != [{"seed": i, "filename": f"seed_{i}.pt", "bytes": 76105,
                      "sha256": frozen_seed_map[str(i)]} for i in range(5)]):
        raise ValueError("Original checkpoint seeds/hashes do not match")

    frozen_rules = inventory["r0_v2"]["rules"]
    if (len(frozen_rules) != 5 or
        candidate["inherited_symbolic"]["r0_v2_manifest_sha256"] !=
            inventory["r0_v2"]["manifest_sha256"] or
        primary["r0_v2"]["manifest_sha256"] != inventory["r0_v2"]["manifest_sha256"]):
        raise ValueError("Frozen R0 inventory diverges")
    expected_rules = [
        {"seed": i, "relative_path": f"data/rules/system_b_r0_v2/seed_{i}.json",
         "normalized_text_sha256": rule["text_sha256"],
         "artifact_sha256": rule["artifact_sha256"]}
        for i, rule in enumerate(sorted(frozen_rules, key=lambda r: r["seed"]))
    ]
    if (set(rule["seed"] for rule in frozen_rules) != set(range(5)) or
        checkpoints.get("r0_rule_files") != expected_rules):
        raise ValueError("Original symbolic R0 identities do not match")

    # A receipt identity pass is NOT real C/D matched-state verification.
    return {
        "scope": "stage10a-accepted-source-only-evidence-recheck-v1",
        "source_receipt_verified": True,
        "original_checkpoint_receipt_verified": True,
        "original_checkpoint_seeds_verified": 5,
        "r0_rule_seeds_verified": 5,
        "matched_three_arm_neural_execution_verified": False,
        "prediction_before_label_runtime_verified": False,
        "independent_environment_experiment_verified": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
        "status": "HOLD_NON_OUTCOME_EVIDENCE_ONLY",
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Stage-10A source evidence recheck; NO treatments")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(assess(args.root), sort_keys=True))


if __name__ == "__main__":
    main()
