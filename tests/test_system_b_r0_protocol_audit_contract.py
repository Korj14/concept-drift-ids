from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "results" / "audits" / "system_b_r0_protocol_audit_v1.json"
EXPECTED_FILE_SHA256 = (
    "abfcb3af93531369427489fc27773f41e500a57279b0fa752b946c3985ebbf32"
)


def test_frozen_r0_protocol_audit_contract() -> None:
    assert AUDIT.is_file()
    digest = hashlib.sha256(AUDIT.read_bytes()).hexdigest()
    assert digest == EXPECTED_FILE_SHA256

    payload = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert payload["source_system_manifest_sha256"] == (
        "6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8"
    )
    assert payload["data_access"] == {
        "training_used": True,
        "development_used": False,
        "pre_drift_used": False,
        "post_drift_used": False,
    }
    assert payload["summary"] == {
        "total_leaf_count": 62,
        "protocol_mismatch_count": 7,
        "active_r0_protocol_mismatch_count": 4,
        "path_rebuild_mismatch_count": 0,
        "stored_unweighted_semantics_mismatch_count": 0,
    }
