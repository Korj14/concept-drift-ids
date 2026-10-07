from __future__ import annotations

import hashlib
import json
from pathlib import Path

from concept_drift_ids.symbolic import canonical_json_hash
from concept_drift_ids.system_b_r0_v2 import (
    ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256,
    AUDIT_FILE_SHA256,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "system_b_v2.json"
EXPECTED_RULE_RAW = {
    0: "d84aecb25c1645745bab08449e8b79f5c5485631847673a274ec9b3bcbef627f",
    1: "bb59e5ef4e819df785dbb2af55a376f2a9ef62d87c78cdb9ea1d2d5502cc50e6",
    2: "ea04c858de1b7a74ab33c07dac34b3b3cf507d2b0239dc4e9d82cb81d7f88829",
    3: "ed11d3e769174cab4d09a7a8c1ad8dd031d729e3d4b8c6ddb984eb6284808899",
    4: "b6fa780fb10a3b4802aa334e929e0480a863bce5ffc593e457dbf2516b3760db",
}
EXPECTED_RULE_CANONICAL = {
    0: "7a214653d56c4ba4c2803af1560b4c28e4c22d709309fb3aa5d9cc06c56636ed",
    1: "bc4bed6e64fced832dd78a796e7eb32468bb90f95317863c482796a5a8044aaf",
    2: "dbcf86b1be9b458e2f37aa4ddc4c1a5683e1d660205eae43957c33506d5dcac6",
    3: "1ef1f1f1fb1ee2285f4fcc37962b16411cbe62e78a96412fb241c0ef42b6ccdb",
    4: "1472e4fd9421ee379946e07cce8a884c72a290a357fe02ad2b359da756e2eaa4",
}
EXPECTED_ACTIVE = {0: 7, 1: 6, 2: 7, 3: 6, 4: 6}
EXPECTED_THRESHOLDS = {
    0: 0.692427396774292,
    1: 0.9354645609855652,
    2: 0.8299936652183533,
    3: 0.9747405052185059,
    4: 0.9527904391288757,
}
EXPECTED_CHANGED = {
    0: set(),
    1: {"s1-leaf5", "s1-leaf8", "s1-leaf15"},
    2: {"s2-leaf8"},
    3: {"s3-leaf4", "s3-leaf15"},
    4: {"s4-leaf8"},
}


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_frozen_r0_v2_contract() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    stored = manifest["manifest_sha256"]
    core = dict(manifest)
    core.pop("manifest_sha256")

    assert stored == ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256
    assert canonical_json_hash(core) == stored
    assert manifest["rule_base_version"] == "R0.v2"
    assert manifest["source_system_b_v1_manifest_sha256"] == (
        "6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8"
    )
    assert manifest["source_protocol_audit_file_sha256"] == AUDIT_FILE_SHA256
    assert manifest["build_git"] == {
        "commit": "cf28304e2f08be731c3ebaf096f4f31fd66eaef7",
        "branch": "stage4-system-b",
        "clean": "true",
    }
    assert manifest["data_access"] == {
        "training_used": True,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }
    assert manifest["fusion"]["selected_neural_weight"] == 0.5

    changed_total = 0
    active_total = 0
    for seed in range(5):
        entry = manifest["rule_artifacts"][str(seed)]
        path = ROOT / entry["path"]
        assert path.is_file()
        assert _file_hash(path) == EXPECTED_RULE_RAW[seed]
        assert entry["sha256"] == EXPECTED_RULE_RAW[seed]
        assert entry["artifact_sha256"] == EXPECTED_RULE_CANONICAL[seed]
        assert entry["active_rule_count"] == EXPECTED_ACTIVE[seed]

        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact_core = dict(payload)
        stored_artifact = artifact_core.pop("artifact_sha256")
        assert canonical_json_hash(artifact_core) == stored_artifact
        assert stored_artifact == EXPECTED_RULE_CANONICAL[seed]
        assert len(payload["rules"]) == EXPECTED_ACTIVE[seed]
        active_total += len(payload["rules"])

        changed = {
            row["candidate"]
            for row in payload["candidate_log"]
            if row.get("consequent_changed_by_protocol_correction") is True
        }
        assert changed == EXPECTED_CHANGED[seed]
        changed_total += len(changed)
        for row in payload["candidate_log"]:
            if row.get("consequent_changed_by_protocol_correction") is True:
                assert row["source_v1_consequent"] == 0
                assert row["consequent"] == 1
                assert row["accepted_by_quality_gate"] is False

        assert manifest["fusion"]["per_seed_thresholds"][str(seed)] == (
            EXPECTED_THRESHOLDS[seed]
        )

    assert changed_total == 7
    assert active_total == 32
