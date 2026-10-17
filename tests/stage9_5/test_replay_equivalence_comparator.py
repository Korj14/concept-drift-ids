from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.stage9_5.replay_equivalence_comparator import (
    NORMALIZED_DIAGNOSTIC,
    PHASE_B_RECORD_TIMING_FIELDS,
    _canonical_sha256,
    _project_phase_a_manifest,
    _project_phase_b_maintenance_record,
    _git_head,
    _verify_stage1_reconstruction_report,
    compare_phase_a_seed,
    compare_phase_b_arm,
    compare_phase_b_seed,
    compare_phase_c_corrected_output,
    compare_phase_c_preconditions,
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

def _rewrite_phase_b_seed_manifest(
    root: Path,
    payload: dict[str, Any],
) -> None:
    body = dict(payload)
    body.pop("payload_sha256", None)
    body.pop("manifest_sha256", None)
    body["manifest_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(root / "phase_b_manifest.json", body)


def test_phase_b_seed_rejects_forged_arm_manifest_identity(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    fresh = _write_phase_b_seed_fixture(tmp_path / "fresh")
    arms = fresh["arms"]
    assert isinstance(arms, dict)
    descriptor = arms["d_drift"]
    assert isinstance(descriptor, dict)
    descriptor["manifest_sha256"] = "9" * 64
    _rewrite_phase_b_seed_manifest(tmp_path / "fresh", fresh)

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert (
        "fresh:d_drift:arm_manifest_identity_mismatch"
        in result["failures"]
    )


def test_phase_b_seed_rejects_redirected_arm_descriptor_path(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    fresh = _write_phase_b_seed_fixture(tmp_path / "fresh")
    arms = fresh["arms"]
    assert isinstance(arms, dict)
    descriptor = arms["d_drift"]
    assert isinstance(descriptor, dict)
    redirected = tmp_path / "fresh" / "d_periodic" / "arm_manifest.json"
    redirected_payload = json.loads(redirected.read_text(encoding="utf-8"))
    descriptor["path"] = "d_periodic/arm_manifest.json"
    descriptor["sha256"] = _sha256_file(redirected)
    descriptor["manifest_sha256"] = str(
        redirected_payload["manifest_sha256"]
    )
    _rewrite_phase_b_seed_manifest(tmp_path / "fresh", fresh)

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "phase_b_manifest.arms.d_drift.path" in result["mismatches"]

REPO_ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_CORRECTION_CONFIG = (
    REPO_ROOT / "data" / "manifests" / "cd_primary_run_config_v1_1.json"
)
ACCEPTED_FAILED_PHASE_C = (
    REPO_ROOT
    / "results"
    / "frozen"
    / "cd_primary_v1"
    / "phase_c_failed_v1"
    / "seed-0"
)


def _rewrite_hashed_json(path: Path, payload: dict[str, Any]) -> None:
    body = copy.deepcopy(payload)
    body.pop("payload_sha256", None)
    body.pop("manifest_sha256", None)
    body["manifest_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    path.write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fresh_correction_config() -> dict[str, Any]:
    payload = json.loads(ACCEPTED_CORRECTION_CONFIG.read_text(encoding="utf-8"))
    reused = payload["correction"]["reused_upstream_artifacts"]
    for seed in range(5):
        key = str(seed)
        reused["phase_a"][key]["run_manifest_sha256"] = hashlib.sha256(
            f"fresh-phase-a-{seed}".encode()
        ).hexdigest()
        reused["phase_b"][key]["phase_b_manifest_sha256"] = hashlib.sha256(
            f"fresh-phase-b-{seed}".encode()
        ).hexdigest()
    return payload


def _write_phase_c_upstream_bindings(
    root: Path,
    config: dict[str, Any],
) -> None:
    reused = config["correction"]["reused_upstream_artifacts"]
    for seed in range(5):
        key = str(seed)
        a_root = root / "phase_a_shared_control_plane" / f"seed-{seed}"
        b_root = root / "phase_b_symbolic_arms" / f"seed-{seed}"
        a_root.mkdir(parents=True, exist_ok=True)
        b_root.mkdir(parents=True, exist_ok=True)
        (a_root / "run_manifest.json").write_text(
            json.dumps(
                {
                    "manifest_sha256": reused["phase_a"][key][
                        "run_manifest_sha256"
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (b_root / "phase_b_manifest.json").write_text(
            json.dumps(
                {
                    "manifest_sha256": reused["phase_b"][key][
                        "phase_b_manifest_sha256"
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )


def _copy_failed_phase_c_lineage(root: Path) -> None:
    target = root / "phase_c_offline_evaluation" / "seed-0"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("attempt.json", "failure.json"):
        (target / name).write_bytes((ACCEPTED_FAILED_PHASE_C / name).read_bytes())


def _phase_c_precondition_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    accepted = json.loads(
        ACCEPTED_CORRECTION_CONFIG.read_text(encoding="utf-8")
    )
    fresh = _fresh_correction_config()

    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    _write_phase_c_upstream_bindings(accepted_root, accepted)
    _write_phase_c_upstream_bindings(fresh_root, fresh)
    _copy_failed_phase_c_lineage(accepted_root)
    _copy_failed_phase_c_lineage(fresh_root)

    fresh_config_path = tmp_path / "fresh_config.json"
    _rewrite_hashed_json(fresh_config_path, fresh)
    return accepted_root, fresh_root, fresh_config_path


def test_phase_c_preconditions_accept_only_rebound_upstream_manifest_hashes(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["mismatch_count"] == 0
    assert result["failed_lineage_preserved"] is True
    assert result["scientific_blocks_equal"] is True


def test_phase_c_preconditions_reject_scientific_block_change(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )
    fresh = json.loads(fresh_config_path.read_text(encoding="utf-8"))
    fresh["fusion"]["primary_neural_weight"] = 0.7
    _rewrite_hashed_json(fresh_config_path, fresh)

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "scientific_block_mismatch:fusion" in result["failures"]


def test_phase_c_preconditions_reject_unbound_fresh_upstream_hash(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )
    wrong = fresh_root / "phase_a_shared_control_plane" / "seed-2" / "run_manifest.json"
    wrong.write_text(
        json.dumps({"manifest_sha256": "f" * 64}) + "\n",
        encoding="utf-8",
    )

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh_correction:phase_a_upstream_manifest_mismatch:2"
        in result["failures"]
    )


def test_phase_c_preconditions_reject_extra_failed_lineage_file(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )
    extra = fresh_root / "phase_c_offline_evaluation" / "seed-0" / "extra.json"
    extra.write_text("{}\n", encoding="utf-8")

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "fresh:failed_lineage_entries_mismatch" in result["failures"]

def _write_phase_a_shared_identity_fixture(
    root: Path,
    *,
    identity_sha256: str = "1" * 64,
) -> None:
    core: dict[str, Any] = {
        "schema_version": 1,
        "seed": 0,
        "shared_identity": {
            "identity_sha256": identity_sha256,
        },
    }
    body = dict(core)
    body["payload_sha256"] = _canonical_sha256(core)
    _write_json_bytes(root / "shared_identity.json", body)


def _write_correction_config_fixture(
    path: Path,
    *,
    tag: str,
    stream_rows: int = 2,
) -> dict[str, Any]:
    core: dict[str, Any] = {
        "schema_version": 1,
        "tag": tag,
        "scenario": {
            "stream_rows": stream_rows,
        },
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(path, body)
    return body


def _write_phase_c_trace(path: Path) -> dict[str, Any]:
    raw = (
        b'{"row_id":"r0","decision":0}\n'
        b'{"row_id":"r1","decision":1}\n'
    )
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compressed)
    return {
        "path": path.name,
        "row_count": 2,
        "sha256": hashlib.sha256(compressed).hexdigest(),
        "canonical_jsonl_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _write_phase_c_evaluation_fixture(
    output_root: Path,
    *,
    arm: str,
    config_sha256: str,
    phase_b_arm_manifest: dict[str, Any],
    metric_value: float = 0.9,
) -> dict[str, Any]:
    trace = _write_phase_c_trace(
        output_root / f"{arm}_prediction_trace.jsonl.gz"
    )
    core: dict[str, Any] = {
        "seed": 0,
        "arm": arm,
        "primary_config_manifest_sha256": config_sha256,
        "phase_b_arm_manifest_sha256": phase_b_arm_manifest[
            "manifest_sha256"
        ],
        "shared_identity_sha256": "1" * 64,
        "metrics_by_neural_weight": {
            "0.5": {
                "post": {
                    "mcc": metric_value,
                }
            }
        },
        "explanation": {
            "mcsc": 0.7,
        },
        "primary_windows": {
            "post": [],
        },
        "primary_recovery": {
            "mcc": {
                "recovery_rows_from_boundary": 0,
            }
        },
        "maintenance_summary": copy.deepcopy(
            phase_b_arm_manifest["maintenance_summary"]
        ),
        "prediction_trace": trace,
    }
    body = dict(core)
    body["summary_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(
        output_root / f"{arm}_evaluation.json",
        body,
    )
    return body


def _write_phase_c_seed_manifest_fixture(
    output_root: Path,
    *,
    config_sha256: str,
    phase_a_manifest_sha256: str,
    phase_b_manifest_sha256: str,
    arm_summaries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    core: dict[str, Any] = {
        "schema_version": 1,
        "seed": 0,
        "status": "complete_offline_evaluation",
        "primary_config_manifest_sha256": config_sha256,
        "phase_a_run_manifest_sha256": phase_a_manifest_sha256,
        "phase_b_seed_manifest_sha256": phase_b_manifest_sha256,
        "arm_summary_sha256": {
            arm: summary["summary_sha256"]
            for arm, summary in arm_summaries.items()
        },
        "lambda_one_predictive_equality": True,
        "trigger_diagnostics": {
            "publication_count": 3,
        },
        "neural_retention_probes": {
            "pre_mcc": 0.8,
        },
        "boundary_index": 69260,
        "adaptive_components_received_boundary": False,
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(output_root / "phase_c_seed_manifest.json", body)
    return body


def _rewrite_phase_c_evaluation(
    path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = copy.deepcopy(payload)
    body.pop("payload_sha256", None)
    body.pop("summary_sha256", None)
    body["summary_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(path, body)
    return body


def _rewrite_phase_c_seed_manifest(
    path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = copy.deepcopy(payload)
    body.pop("payload_sha256", None)
    body.pop("manifest_sha256", None)
    body["manifest_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(path, body)
    return body


def _phase_c_corrected_output_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"

    accepted_phase_a = _write_phase_a_fixture(
        accepted_root / "phase_a_shared_control_plane" / "seed-0",
        platform="accepted-platform",
        processor="accepted-cpu",
        filepath="C:/accepted/lib.dll",
    )
    fresh_phase_a = _write_phase_a_fixture(
        fresh_root / "phase_a_shared_control_plane" / "seed-0",
        platform="fresh-platform",
        processor="fresh-cpu",
        filepath="D:/fresh/lib.dll",
    )
    _write_phase_a_shared_identity_fixture(
        accepted_root / "phase_a_shared_control_plane" / "seed-0"
    )
    _write_phase_a_shared_identity_fixture(
        fresh_root / "phase_a_shared_control_plane" / "seed-0"
    )

    accepted_phase_b = _write_phase_b_seed_fixture(
        accepted_root / "phase_b_symbolic_arms" / "seed-0",
        timing_scale=1.0,
    )
    fresh_phase_b = _write_phase_b_seed_fixture(
        fresh_root / "phase_b_symbolic_arms" / "seed-0",
        timing_scale=9.0,
    )

    accepted_config_path = tmp_path / "accepted_phase_c_config.json"
    fresh_config_path = tmp_path / "fresh_phase_c_config.json"
    accepted_config = _write_correction_config_fixture(
        accepted_config_path,
        tag="accepted",
    )
    fresh_config = _write_correction_config_fixture(
        fresh_config_path,
        tag="fresh",
    )

    for root, config, phase_a, phase_b in (
        (
            accepted_root,
            accepted_config,
            accepted_phase_a,
            accepted_phase_b,
        ),
        (
            fresh_root,
            fresh_config,
            fresh_phase_a,
            fresh_phase_b,
        ),
    ):
        output_root = (
            root / "phase_c_offline_evaluation_v1_1" / "seed-0"
        )
        output_root.mkdir(parents=True, exist_ok=True)
        summaries: dict[str, dict[str, Any]] = {}
        for arm in ("c_frozen_symbolic", "d_drift", "d_periodic"):
            arm_manifest = json.loads(
                (
                    root
                    / "phase_b_symbolic_arms"
                    / "seed-0"
                    / arm
                    / "arm_manifest.json"
                ).read_text(encoding="utf-8")
            )
            summaries[arm] = _write_phase_c_evaluation_fixture(
                output_root,
                arm=arm,
                config_sha256=str(config["manifest_sha256"]),
                phase_b_arm_manifest=arm_manifest,
            )
        _write_phase_c_seed_manifest_fixture(
            output_root,
            config_sha256=str(config["manifest_sha256"]),
            phase_a_manifest_sha256=str(phase_a["manifest_sha256"]),
            phase_b_manifest_sha256=str(phase_b["manifest_sha256"]),
            arm_summaries=summaries,
        )

    return (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    )


def test_phase_c_corrected_output_accepts_only_transitive_identity_and_timing(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["mismatch_count"] == 0


def test_phase_c_corrected_output_rejects_scientific_metric_change(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    output_root = (
        fresh_root / "phase_c_offline_evaluation_v1_1" / "seed-0"
    )
    path = output_root / "d_drift_evaluation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics_by_neural_weight"]["0.5"]["post"]["mcc"] = 0.1
    rewritten = _rewrite_phase_c_evaluation(path, payload)

    seed_path = output_root / "phase_c_seed_manifest.json"
    seed_payload = json.loads(seed_path.read_text(encoding="utf-8"))
    seed_payload["arm_summary_sha256"]["d_drift"] = rewritten[
        "summary_sha256"
    ]
    _rewrite_phase_c_seed_manifest(seed_path, seed_payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert any(
        "metrics_by_neural_weight" in path
        for path in result["mismatches"]
    )


def test_phase_c_corrected_output_rejects_prediction_trace_byte_tamper(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    trace = (
        fresh_root
        / "phase_c_offline_evaluation_v1_1"
        / "seed-0"
        / "d_drift_prediction_trace.jsonl.gz"
    )
    trace.write_bytes(trace.read_bytes() + b"tamper")

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh:d_drift:prediction_trace_file_sha256_mismatch"
        in result["failures"]
    )


def test_phase_c_corrected_output_rejects_shared_identity_rebinding(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    shared_path = (
        fresh_root
        / "phase_a_shared_control_plane"
        / "seed-0"
        / "shared_identity.json"
    )
    shared = json.loads(shared_path.read_text(encoding="utf-8"))
    shared["shared_identity"]["identity_sha256"] = "9" * 64
    shared.pop("payload_sha256", None)
    shared["payload_sha256"] = _canonical_sha256(shared)
    _write_json_bytes(shared_path, shared)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh:d_drift:shared_identity_binding_mismatch"
        in result["failures"]
    )


def test_phase_c_corrected_output_rejects_seed_control_change(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    seed_path = (
        fresh_root
        / "phase_c_offline_evaluation_v1_1"
        / "seed-0"
        / "phase_c_seed_manifest.json"
    )
    seed_payload = json.loads(seed_path.read_text(encoding="utf-8"))
    seed_payload["lambda_one_predictive_equality"] = False
    _rewrite_phase_c_seed_manifest(seed_path, seed_payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "fresh:phase_c_lambda_one_control_failed" in result["failures"]

def _write_stage1_contract_and_report(
    tmp_path: Path,
    *,
    repository_head: str,
    status: str = "pass",
) -> tuple[Path, Path]:
    verifier_path = tmp_path / "stage1_verifier.py"
    verifier_path.write_text("# frozen toy verifier\n", encoding="utf-8")
    contract = {
        "contract_id": "stage9.5-6-stage1-reconstruction-evidence-v1",
        "verifier_implementation": {
            "verifier_id": "stage9.5-6-stage1-reconstruction-verifier-v1",
            "tool_path": "stage1_verifier.py",
        },
        "required_report": {
            "path": "stage1_reconstruction_report.json",
            "audit_id": "stage9.5-6-stage1-reconstruction-v1",
            "required_success_values": {
                "status": "pass",
                "pass": True,
                "raw_file_count_verified": 8,
                "interim_table_count_verified": 8,
                "preprocessing_manifest_canonical_sha256": "d" * 64,
                "semantic_mismatch_count": 0,
                "failures": [],
                "blockers": [],
            },
        },
    }
    contract_path = tmp_path / "stage1_contract.json"
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = {
        "audit_id": "stage9.5-6-stage1-reconstruction-v1",
        "contract_id": contract["contract_id"],
        "contract_canonical_sha256": _canonical_sha256(contract),
        "verifier_id": contract["verifier_implementation"]["verifier_id"],
        "verifier_source_sha256": _sha256_file(verifier_path),
        "status": status,
        "pass": status == "pass",
        "repository_head": repository_head,
        "manual_success_override_permitted": False,
        "raw_file_count_verified": 8,
        "interim_table_count_verified": 8,
        "preprocessing_manifest_canonical_sha256": "d" * 64,
        "semantic_mismatch_count": 0,
        "failures": [] if status == "pass" else ["toy_failure"],
        "blockers": [],
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
    }
    report["canonical_sha256"] = _canonical_sha256(report)
    report_path = tmp_path / "stage1_reconstruction_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return contract_path, report_path


def test_stage1_report_binding_accepts_canonical_ancestor_report(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["canonical_sha256"] is not None


def test_stage1_report_binding_rejects_resealed_semantic_failure(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
        status="blocked",
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert "stage1_report_success_value_mismatch:status" in result["failures"]
    assert "stage1_report_success_value_mismatch:pass" in result["failures"]
    assert "stage1_report_success_value_mismatch:failures" in result["failures"]


def test_stage1_report_binding_rejects_unrelated_repository_head(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head="f" * 40,
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert "stage1_report_repository_head_not_ancestor" in result["failures"]

def test_stage1_report_binding_rejects_wrong_contract_identity(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["contract_canonical_sha256"] = "0" * 64
    report.pop("canonical_sha256", None)
    report["canonical_sha256"] = _canonical_sha256(report)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert (
        "stage1_report_contract_canonical_sha256_mismatch"
        in result["failures"]
    )


def test_stage1_report_binding_rejects_wrong_verifier_source_identity(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["verifier_source_sha256"] = "0" * 64
    report.pop("canonical_sha256", None)
    report["canonical_sha256"] = _canonical_sha256(report)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert (
        "stage1_report_verifier_source_sha256_mismatch"
        in result["failures"]
    )

def test_committed_stage1_reconstruction_report_passes_binding() -> None:
    report_path = (
        Path(__file__).resolve().parents[2]
        / "results"
        / "audits"
        / "stage9_5_full_seed_rerun_v1"
        / "stage1_reconstruction_report.json"
    )
    assert report_path.is_file()

    result = _verify_stage1_reconstruction_report(report_path)

    assert result["pass"] is True
    assert result["failures"] == []
    assert (
        result["canonical_sha256"]
        == "4bafa772f9737d934f40c90bf7be8d80a62108cf89a9c74895fbe5c12c4a88af"
    )

def _project_phase_b_record_sequence(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_project_phase_b_maintenance_record(record) for record in records]


def test_phase_b_record_projection_contract_matches_frozen_v1_1_surface() -> None:
    root = Path(__file__).resolve().parents[2]
    contract_path = (
        root
        / "data"
        / "manifests"
        / "stage9_5_6_phase_b_maintenance_record_projection_v1.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert contract["contract_id"] == (
        "stage9.5-6-phase-b-maintenance-record-projection-v1"
    )
    assert contract["permitted_record_projection"]["top_level_fields_removed"] == [
        "shap_seconds",
        "surrogate_seconds",
        "lifecycle_seconds",
    ]
    assert contract["permitted_record_projection"]["nested_direct_child_removed"] == [
        "generation_payload.timing_seconds"
    ]
    assert tuple(PHASE_B_RECORD_TIMING_FIELDS) == (
        "shap_seconds",
        "surrogate_seconds",
        "lifecycle_seconds",
    )
    assert contract["permitted_record_projection"]["diagnostic_exclusion_set_closed"] is True
    assert contract["permitted_record_projection"]["no_name_pattern_matching"] is True
    assert contract["permitted_record_projection"]["no_recursive_timing_field_removal"] is True
    assert contract["arm_manifest_transitive_hash_handling_frozen_by_this_contract"] is False
    assert contract["seed_manifest_transitive_hash_handling_frozen_by_this_contract"] is False


def test_phase_b_record_projection_ignores_exactly_predeclared_timing_paths() -> None:
    accepted = {
        "record_id": "r-1",
        "scientific_value": {"score": 0.75},
        "shap_seconds": 1.0,
        "surrogate_seconds": 2.0,
        "lifecycle_seconds": 3.0,
        "generation_payload": {
            "generation_evidence_id": "a" * 64,
            "scientific_value": {"kept": True},
            "timing_seconds": {
                "shap": 1.25,
                "surrogate": 2.25,
            },
            "timing_seconds_extra": "must-remain-exact",
            "nested": {"timing_seconds": "also-must-remain-exact"},
        },
        "other": {"timing_seconds": "must-remain-exact"},
    }
    fresh = copy.deepcopy(accepted)
    fresh["shap_seconds"] = 100.0
    fresh["surrogate_seconds"] = 200.0
    fresh["lifecycle_seconds"] = 300.0
    fresh["generation_payload"]["timing_seconds"] = [
        "different",
        {"shape": "entire-direct-child-is-diagnostic"},
    ]

    assert _project_phase_b_maintenance_record(accepted) == (
        _project_phase_b_maintenance_record(fresh)
    )


def test_phase_b_record_projection_preserves_non_timing_generation_payload_fields() -> None:
    accepted = {
        "record_id": "r-1",
        "generation_payload": {
            "generation_evidence_id": "a" * 64,
            "timing_seconds": {"shap": 1.0},
            "nested": {"timing_seconds": "scientific-here"},
        },
    }
    fresh = copy.deepcopy(accepted)
    fresh["generation_payload"]["nested"]["timing_seconds"] = "changed"

    assert _project_phase_b_maintenance_record(accepted) != (
        _project_phase_b_maintenance_record(fresh)
    )


def test_phase_b_record_projection_preserves_generation_payload_parent_semantics() -> None:
    missing = {"record_id": "r-1"}
    null = {"record_id": "r-1", "generation_payload": None}
    object_value = {
        "record_id": "r-1",
        "generation_payload": {"timing_seconds": 1.0},
    }

    missing_projected = _project_phase_b_maintenance_record(missing)
    null_projected = _project_phase_b_maintenance_record(null)
    object_projected = _project_phase_b_maintenance_record(object_value)

    assert "generation_payload" not in missing_projected
    assert null_projected["generation_payload"] is None
    assert object_projected["generation_payload"] == {}
    assert missing_projected != null_projected
    assert null_projected != object_projected
    assert missing_projected != object_projected


def test_phase_b_record_projection_rejects_non_object_generation_payload() -> None:
    try:
        _project_phase_b_maintenance_record(
            {"record_id": "r-1", "generation_payload": "invalid"}
        )
    except TypeError as exc:
        assert "generation_payload must be an object or null" in str(exc)
    else:
        raise AssertionError("Non-object generation_payload must fail closed")


def test_phase_b_record_sequence_missing_added_and_reordered_records_fail_closed() -> None:
    accepted = [
        {"record_id": "r-1", "scientific_value": 1, "shap_seconds": 1.0},
        {"record_id": "r-2", "scientific_value": 2, "shap_seconds": 2.0},
    ]
    missing = [copy.deepcopy(accepted[0])]
    added = copy.deepcopy(accepted) + [
        {"record_id": "r-3", "scientific_value": 3, "shap_seconds": 3.0}
    ]
    reordered = [copy.deepcopy(accepted[1]), copy.deepcopy(accepted[0])]

    accepted_projected = _project_phase_b_record_sequence(accepted)
    missing_projected = _project_phase_b_record_sequence(missing)
    added_projected = _project_phase_b_record_sequence(added)
    reordered_projected = _project_phase_b_record_sequence(reordered)

    assert accepted_projected != missing_projected
    assert accepted_projected != added_projected
    assert accepted_projected != reordered_projected
    assert _canonical_sha256(accepted_projected) != _canonical_sha256(missing_projected)
    assert _canonical_sha256(accepted_projected) != _canonical_sha256(added_projected)
    assert _canonical_sha256(accepted_projected) != _canonical_sha256(reordered_projected)


def test_phase_b_record_sequence_non_timing_change_fails_closed() -> None:
    accepted = [
        {
            "record_id": "r-1",
            "scientific_value": {"decision": "publish"},
            "generation_payload": {
                "generation_evidence_id": "a" * 64,
                "timing_seconds": {"shap": 1.0},
            },
        }
    ]
    fresh = copy.deepcopy(accepted)
    fresh[0]["scientific_value"]["decision"] = "retire"

    assert _project_phase_b_record_sequence(accepted) != (
        _project_phase_b_record_sequence(fresh)
    )

