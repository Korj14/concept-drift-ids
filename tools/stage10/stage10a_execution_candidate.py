"""Validate the Stage-10A pre-outcome executable-binding CANDIDATE.

The candidate is a derived implementation artifact, never a second source
of scientific authority. This module only verifies configuration and tracked
file identities. It NEVER loads data, checkpoints, or treatment outcomes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from tools.stage10.stage10a_isolation_contract import verify_preoutcome_configuration

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "data/manifests/stage10a_execution_candidate_v1.json"
MASTER = ROOT / "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json"
STAGE = ROOT / "data/manifests/stage10a_goldeneye_attack_pattern_v1.json"
PRIMARY = ROOT / "data/manifests/cd_primary_run_config_v1_1.json"
FROZEN_BLOBS = {
    "master_manifest_git_blob_sha1": ("data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json", "8ac82c8d907243556a5673d09600cd1bdc19aa52"),
    "master_protocol_git_blob_sha1": ("STAGE10_PLUS_MASTER_REPLICATION_SENSITIVITY_PROTOCOL_V1_1.md", "ac61908d30bcc26cddbe6467d807a3de119689d9"),
    "stage10a_manifest_git_blob_sha1": ("data/manifests/stage10a_goldeneye_attack_pattern_v1.json", "001501350fbf9fa4a4075176b9af43c2cf275bc5"),
    "stage10a_protocol_git_blob_sha1": ("STAGE10A_GOLDENEYE_ATTACK_PATTERN_REPLICATION_PROTOCOL_V1.md", "2785e94380cc29e20f014738e2837d708649f5bc"),
    "source_audit_git_blob_sha1": ("data/manifests/stage10a_goldeneye_source_audit_v1.json", "a9700114cc08b0525b1a77fe2e499152d94ccb26"),
    "primary_run_config_git_blob_sha1": ("data/manifests/cd_primary_run_config_v1_1.json", "7ba598fec1cf8ce92f804d4123afbf01ec310b23"),
}


def tracked_blob_identity(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    ).hexdigest()


def derive_expected(
    master: Mapping[str, Any],
    stage: Mapping[str, Any],
    primary: Mapping[str, Any],
) -> dict[str, Any]:
    """Re-derive all scientific values from frozen authority, never candidates."""
    verify_preoutcome_configuration(master, stage, primary)
    authorities = {
        key: sha for key, (_, sha) in FROZEN_BLOBS.items()
    }
    authorities.update({
        "source_audit_canonical_sha256": stage["source_audit"]["canonical_sha256"],
        "stage10a_manifest_canonical_sha256": stage["canonical_sha256"],
        "primary_run_config_manifest_sha256": primary["manifest_sha256"],
    })
    return {
        "schema_version": 1,
        "candidate_id": "stage10a-goldeneye-executable-binding-candidate-v1",
        "status": "preoutcome_candidate_hold_not_executable",
        "governance": {
            "stage10_execution_permitted": False,
            "stage10a_treatment_execution_authorized": False,
            "stage10_treatment_outcomes_accessed": False,
            "stage10a_treatment_outcomes_accessed": False,
            "release_signed": False,
            "requires_separate_release": True,
        },
        "authorities": authorities,
        "source_only": {
            "raw_source": stage["raw_source"],
            "scenario_id": stage["scenario_id"],
            "scenario": stage["scenario"],
            "source_receipt_required": True,
            "source_receipt_status": "not_yet_accepted_exact_python_3_11_9",
            "feature_count": 77,
            "preprocessing_state_sha256": stage["inherited_identities"]["preprocessing_core_state_sha256"],
            "train_development_preexisting": True,
            "boundary_offline_only": True,
        },
        "arms": {
            "names": stage["primary_arms"],
            "seeds": stage["inherited_identities"]["seeds"],
            "causal_unit": stage["causal_unit"],
            "shared_neural_trajectory_per_seed_required": True,
            "shared_trace_real_provenance_verified": False,
        },
        "inherited_neural": {
            "checkpoint_sha256_by_seed": primary["system_a"]["checkpoint_sha256_by_seed"],
            "system_a_manifest_sha256": primary["system_a"]["manifest_sha256"],
            "monitor_threshold_by_seed": primary["system_a"]["monitor_threshold_by_seed"],
            "primary_control_plane": primary["primary_control_plane"],
            "primary_fusion": {
                "neural_weight": primary["fusion"]["primary_neural_weight"],
                "thresholds_by_seed": primary["fusion"]["thresholds"]["0.5"],
            },
            "requires_original_checkpoint_bytes": True,
        },
        "inherited_symbolic": {
            "r0_v2_manifest_sha256": primary["r0_v2"]["manifest_sha256"],
            "r0_active_rule_counts_by_seed": primary["r0_v2"]["active_rule_counts"],
            "primary_symbolic_operator": primary["primary_symbolic_operator"],
            "generation_window_rows": stage["adaptive_mechanism"]["generation_window_rows"],
            "validation_window_rows": stage["adaptive_mechanism"]["validation_window_rows"],
        },
        "evaluation": {
            "primary_endpoints": stage["primary_endpoints"],
            "confirmatory_unit": stage["causal_unit"],
            "multiplicity": "paired_seeds_0_4_Holm_prospectively_frozen",
            "post_boundary_offline_evaluation_only": True,
            "raw_seed_effects_mandatory": True,
            "claim_boundaries": stage["claim_boundaries"],
        },
        "implementation": {
            "fixed_python_version": "3.11.9",
            "requirements_lock_normalized_sha256": primary["requirements"]["binding_normalized_text_sha256"],
            "cpu_only": True,
            "required_thread_environment": primary["execution"]["required_thread_environment"],
            "phase_order": primary["execution"]["phase_order"],
            "write_once_outputs": True,
            "output_namespace": "artifacts/stage10a_goldeneye_v1",
            "stage10a_execution_entrypoint_exists": False,
            "exact_head_clean_checkout_required": True,
            "real_matched_c_d_isolation_verified": False,
            "source_boundary_and_labels_forbidden_in_observation_events": True,
            "label_latency_rows": stage["information_timing"]["label_latency_rows"],
            "prediction_before_label_release": True,
        },
        "release_blockers": [
            "canonical_source_receipt_clean_python3_11_9",
            "original_system_a_checkpoints_and_r0_bytes_availability",
            "stage10a_execution_entrypoint_and_test_then_update_proof",
            "matched_neural_and_control_trajectory_real_evidence_5_seeds",
            "write_once_run_output_inference_identity",
            "independent_second_dataset_criteria_freeze_master_S10_04",
            "explicit_stage10a_release",
        ],
    }


def verify_candidate(
    candidate: Mapping[str, Any],
    master: Mapping[str, Any],
    stage: Mapping[str, Any],
    primary: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed on any mismatch, unknown field, unauthorized release, or retuning."""
    expected = derive_expected(master, stage, primary)
    if candidate != expected:
        raise ValueError(
            "Stage-10A candidate does not exactly match the frozen authorities."
        )
    if candidate["governance"]["stage10_execution_permitted"] is not False:
        raise ValueError("Stage-10 execution is not authorized.")
    if candidate["governance"]["release_signed"] is not False:
        raise ValueError("This candidate is not a release.")
    return {
        "candidate_consistent": True,
        "execution_authorized": False,
        "source_receipt_accepted": False,
        "real_three_arm_isolation_verified": False,
    }


def verify_from_repository(*, root: Path = ROOT) -> dict[str, Any]:
    """Read tracked repository files only; no model, dataset, or outcome access."""
    documents = (
        json.loads((root / path).read_text(encoding="utf-8"))
        for path in (
            "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json",
            "data/manifests/stage10a_goldeneye_attack_pattern_v1.json",
            "data/manifests/cd_primary_run_config_v1_1.json",
        )
    )
    master, stage, primary = documents
    candidate = json.loads(
        (root / "data/manifests/stage10a_execution_candidate_v1.json").read_text(encoding="utf-8")
    )
    for key, (relative, expected) in FROZEN_BLOBS.items():
        actual = tracked_blob_identity(root / relative)
        if actual != expected or candidate["authorities"][key] != actual:
            raise ValueError(f"Frozen Git blob identity changed: {key}")
    return verify_candidate(candidate, master, stage, primary)


if __name__ == "__main__":
    print(json.dumps(verify_from_repository(), sort_keys=True))
