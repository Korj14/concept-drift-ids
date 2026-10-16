from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.stage9_5.replay_equivalence_comparator import (
    NORMALIZED_DIAGNOSTIC,
    _canonical_sha256,
    _project_phase_a_manifest,
    compare_phase_a_seed,
    compare_phase_b_arm,
    compare_phase_b_seed,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_phase_a_fixture(
    root: Path,
    *,
    platform: str = "platform-a",
    processor: str = "processor-a",
    filepath: str = "C:/env/lib.dll",
    python_version: str = "3.11.9",
    file_bytes: bytes = b'{"row":1}\n',
) -> dict[str, Any]:
    root.mkdir(parents=True)
    data_path = root / "predictions.jsonl"
    data_path.write_bytes(file_bytes)

    core: dict[str, Any] = {
        "schema_version": 1,
        "run_id": "cd-primary-v1-phase-a-seed-0",
        "seed": 0,
        "arm": "shared_control_plane",
        "git_commit": "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645",
        "protocol_hashes": {"protocol": "a" * 64},
        "runtime": {
            "platform": platform,
            "processor": processor,
            "python_implementation": "CPython",
            "python_version": python_version,
            "thread_environment": {
                "OMP_NUM_THREADS": "1",
            },
            "threadpool_info": [
                {
                    "filepath": filepath,
                    "internal_api": "openblas",
                    "num_threads": 1,
                    "version": "0.3.31",
                }
            ],
        },
        "scenario_identity": {
            "primary_config_manifest_sha256": "b" * 64,
            "adaptive_runner_received_boundary_metadata": False,
        },
        "initial_checkpoint_sha256": "c" * 64,
        "preprocessing_sha256": "d" * 64,
        "files": {
            "predictions": {
                "path": "predictions.jsonl",
                "sha256": _sha256_file(data_path),
            }
        },
        "status": "complete_unscored_shared_trajectory",
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    (root / "run_manifest.json").write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return body


def test_phase_a_projection_normalizes_only_frozen_runtime_diagnostics(
    tmp_path: Path,
) -> None:
    accepted = _write_phase_a_fixture(
        tmp_path / "accepted",
        platform="Windows-A",
        processor="CPU-A",
        filepath="C:/accepted/lib.dll",
    )
    fresh = _write_phase_a_fixture(
        tmp_path / "fresh",
        platform="Windows-B",
        processor="CPU-B",
        filepath="D:/fresh/lib.dll",
    )

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is True
    assert result["mismatch_count"] == 0
    assert result["failures"] == []
    assert (
        result["accepted_projected_sha256"]
        == result["fresh_projected_sha256"]
    )
    projected = _project_phase_a_manifest(accepted)
    assert projected["runtime"]["platform"] == NORMALIZED_DIAGNOSTIC
    assert projected["runtime"]["processor"] == NORMALIZED_DIAGNOSTIC
    assert (
        projected["runtime"]["threadpool_info"][0]["filepath"]
        == NORMALIZED_DIAGNOSTIC
    )
    assert "manifest_sha256" not in projected
    assert "payload_sha256" not in projected


def test_phase_a_projection_rejects_non_diagnostic_runtime_change(
    tmp_path: Path,
) -> None:
    _write_phase_a_fixture(tmp_path / "accepted", python_version="3.11.9")
    _write_phase_a_fixture(tmp_path / "fresh", python_version="3.11.10")

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "runtime.python_version" in result["mismatches"]


def test_phase_a_comparator_rejects_descriptor_linked_byte_mismatch(
    tmp_path: Path,
) -> None:
    _write_phase_a_fixture(tmp_path / "accepted")
    _write_phase_a_fixture(tmp_path / "fresh")
    (tmp_path / "fresh" / "predictions.jsonl").write_bytes(b"tampered\n")

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "fresh:file_sha256_mismatch:predictions" in result["failures"]


def test_phase_a_comparator_rejects_forged_manifest_self_hash(
    tmp_path: Path,
) -> None:
    _write_phase_a_fixture(tmp_path / "accepted")
    fresh = _write_phase_a_fixture(tmp_path / "fresh")
    fresh["manifest_sha256"] = "e" * 64
    fresh["payload_sha256"] = _canonical_sha256(
        {k: v for k, v in fresh.items() if k != "payload_sha256"}
    )
    (tmp_path / "fresh" / "run_manifest.json").write_text(
        json.dumps(fresh, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "fresh:manifest_sha256_mismatch" in result["failures"]

def _write_json_bytes(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _sha256_file(path)


def _write_phase_b_arm_fixture(
    root: Path,
    *,
    arm: str,
    seed: int = 0,
    timing_scale: float = 1.0,
    scientific_value: str = "stable",
    state_value: str = "same-state",
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    initial_sha = _write_json_bytes(
        root / "initial_state.json",
        {"state": state_value},
    )
    final_sha = _write_json_bytes(
        root / "final_state.json",
        {"state": state_value},
    )
    maintenance_records = [
        {
            "arm": arm,
            "opportunity_id": 1,
            "opportunity_clock": 100,
            "status": scientific_value,
            "neural_checkpoint_sha256": "a" * 64,
            "generation_evidence_id": "b" * 64,
            "generation_row_ids": ["r1", "r2"],
            "validation_row_ids": ["r3"],
            "validation_completion_clock": 120,
            "symbolic_publication_effective_index": 121,
            "parent_rule_base_version_id": "r0",
            "result_rule_base_version_id": "r1",
            "parent_rule_base_sha256": "c" * 64,
            "result_rule_base_sha256": "d" * 64,
            "history_sha256": "e" * 64,
            "candidate_count": 2,
            "shap_seconds": 1.0 * timing_scale,
            "surrogate_seconds": 2.0 * timing_scale,
            "lifecycle_seconds": 3.0 * timing_scale,
            "validation_wait_rows": 20,
            "generation_payload": {
                "generation_evidence_id": "b" * 64,
                "scientific_value": "same",
                "timing_seconds": {
                    "shap": 1.0 * timing_scale,
                    "surrogate": 2.0 * timing_scale,
                },
            },
            "lifecycle": None,
        }
    ]
    maintenance_path = root / "maintenance.jsonl"
    maintenance_path.write_text(
        "".join(
            json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
            for item in maintenance_records
        ),
        encoding="utf-8",
    )
    maintenance_sha = _sha256_file(maintenance_path)

    compute = 6.0 * timing_scale
    core: dict[str, Any] = {
        "schema_version": 1,
        "seed": seed,
        "arm": arm,
        "operator_config_sha256": "f" * 64,
        "shared_identity_sha256": "1" * 64,
        "initial_rule_base_version_id": "r0",
        "initial_rule_base_sha256": "2" * 64,
        "final_rule_base_version_id": "r1",
        "final_rule_base_sha256": "3" * 64,
        "final_history_sha256": "4" * 64,
        "publications": [],
        "maintenance_summary": {
            "opportunity_count": 1,
            "completed_validation_count": 1,
            "publication_count": 1,
            "no_op_count": 0,
            "censored_or_blocked_count": 0,
            "candidate_count": 2,
            "publication_per_opportunity": 1.0,
            "compute_seconds": compute,
            "shap_seconds": 1.0 * timing_scale,
            "surrogate_seconds": 2.0 * timing_scale,
            "lifecycle_seconds": 3.0 * timing_scale,
            "compute_seconds_per_opportunity": compute,
            "compute_seconds_per_publication": compute,
            "mean_validation_wait_rows": 20.0,
            "lifecycle_decision_counts": {"retained": 1},
        },
        "files": {
            "initial_state": {
                "path": "initial_state.json",
                "sha256": initial_sha,
            },
            "final_state": {
                "path": "final_state.json",
                "sha256": final_sha,
            },
            "maintenance": {
                "path": "maintenance.jsonl",
                "sha256": maintenance_sha,
            },
        },
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(root / "arm_manifest.json", body)
    return body


def _write_phase_b_seed_fixture(
    root: Path,
    *,
    timing_scale: float = 1.0,
    arm_isolation_sha256: str = "5" * 64,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    arms: dict[str, dict[str, str]] = {}
    for arm in ("c_frozen_symbolic", "d_drift", "d_periodic"):
        manifest = _write_phase_b_arm_fixture(
            root / arm,
            arm=arm,
            timing_scale=timing_scale,
        )
        arm_path = root / arm / "arm_manifest.json"
        arms[arm] = {
            "path": f"{arm}/arm_manifest.json",
            "sha256": _sha256_file(arm_path),
            "manifest_sha256": str(manifest["manifest_sha256"]),
        }

    core: dict[str, Any] = {
        "schema_version": 1,
        "run_id": "cd-primary-v1-phase-b-seed-0",
        "seed": 0,
        "git_commit": "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645",
        "status": "complete_unscored_symbolic_trajectories",
        "primary_config_manifest_sha256": "6" * 64,
        "shared_identity_sha256": "1" * 64,
        "all_phase_a_shared_identity_sha256": {
            str(seed): f"{seed}" * 64 for seed in range(5)
        },
        "operator_config_sha256": "f" * 64,
        "arm_isolation_sha256": arm_isolation_sha256,
        "arms": arms,
        "primary_boundary_scored": False,
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(root / "phase_b_manifest.json", body)
    return body


def test_phase_b_arm_accepts_only_predeclared_timing_differences(
    tmp_path: Path,
) -> None:
    _write_phase_b_arm_fixture(
        tmp_path / "accepted",
        arm="d_drift",
        timing_scale=1.0,
    )
    _write_phase_b_arm_fixture(
        tmp_path / "fresh",
        arm="d_drift",
        timing_scale=9.0,
    )

    result = compare_phase_b_arm(
        accepted_arm_root=tmp_path / "accepted",
        fresh_arm_root=tmp_path / "fresh",
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is True
    assert result["mismatch_count"] == 0
    assert result["failures"] == []


def test_phase_b_arm_rejects_scientific_maintenance_change(
    tmp_path: Path,
) -> None:
    _write_phase_b_arm_fixture(
        tmp_path / "accepted",
        arm="d_drift",
        scientific_value="same",
    )
    _write_phase_b_arm_fixture(
        tmp_path / "fresh",
        arm="d_drift",
        scientific_value="changed",
    )

    result = compare_phase_b_arm(
        accepted_arm_root=tmp_path / "accepted",
        fresh_arm_root=tmp_path / "fresh",
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is False
    assert any(
        path.endswith(".status")
        for path in result["mismatches"]
    )


def test_phase_b_arm_rejects_nonmaintenance_state_change(
    tmp_path: Path,
) -> None:
    _write_phase_b_arm_fixture(
        tmp_path / "accepted",
        arm="d_periodic",
        state_value="accepted",
    )
    _write_phase_b_arm_fixture(
        tmp_path / "fresh",
        arm="d_periodic",
        state_value="fresh",
    )

    result = compare_phase_b_arm(
        accepted_arm_root=tmp_path / "accepted",
        fresh_arm_root=tmp_path / "fresh",
        seed=0,
        arm="d_periodic",
    )

    assert result["pass"] is False
    assert (
        "nonmaintenance_file_descriptor_mismatch:initial_state"
        in result["failures"]
    )


def test_phase_b_seed_removes_only_timing_dependent_arm_hashes(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(
        tmp_path / "accepted",
        timing_scale=1.0,
    )
    _write_phase_b_seed_fixture(
        tmp_path / "fresh",
        timing_scale=7.0,
    )

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is True
    assert result["mismatch_count"] == 0
    assert result["failures"] == []


def test_phase_b_seed_keeps_arm_isolation_identity_exact(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(
        tmp_path / "accepted",
        arm_isolation_sha256="5" * 64,
    )
    _write_phase_b_seed_fixture(
        tmp_path / "fresh",
        arm_isolation_sha256="7" * 64,
    )

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "phase_b_manifest.arm_isolation_sha256" in result["mismatches"]

