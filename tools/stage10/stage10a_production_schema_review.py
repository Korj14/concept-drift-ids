"""Read-only Stage-10A production-schema REVIEW candidate guard.

This module is deliberately non-executable: no source CSV, checkpoint, model,
network, treatment, outcome, or RELEASE path. A pass only validates consistency
of a prospective schema proposal with pre-outcome frozen source authorities.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "data/manifests/stage10a_production_schema_review_candidate_v0_1.json"
MASTER = "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json"
STAGE = "data/manifests/stage10a_goldeneye_attack_pattern_v1.json"
PRIMARY = "data/manifests/cd_primary_run_config_v1_1.json"
SOURCE_RECEIPT = "results/audits/stage10a_original_source_receipt_601516ff_2026_10_31.json"
CHECKPOINT_RECEIPT = "results/audits/stage10a_original_checkpoint_source_only_receipt_41156553037.json"
PINNED = {
    MASTER: ("blob", "8ac82c8d907243556a5673d09600cd1bdc19aa52"),
    STAGE: ("blob", "001501350fbf9fa4a4075176b9af43c2cf275bc5"),
    PRIMARY: ("blob", "7ba598fec1cf8ce92f804d4123afbf01ec310b23"),
    SOURCE_RECEIPT: ("sha256", "d6e0874181b4aebe4d259b7f4f66b7d608aaf7803c6dc3c10f0151aaf2f9a42a"),
    CHECKPOINT_RECEIPT: ("sha256", "94cf6ee608e63be4834372aa0be8956eaaf289234f395dd788a9e0d23ba2b1c1"),
}
PHASE_A_STREAMS = (
    "predictions.jsonl", "label_schedule.jsonl", "detector_observations.jsonl",
    "events.jsonl", "replay_transactions.jsonl", "checkpoint_chain.jsonl",
)


def _read_pinned(root: Path, path: str) -> dict[str, Any]:
    target = root / path
    if target.is_symlink() or not target.is_file():
        raise ValueError("Missing or redirected frozen Stage-10A authority")
    raw = target.read_bytes()
    kind, expected = PINNED[path]
    actual = (hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
              if kind == "blob" else hashlib.sha256(raw).hexdigest())
    if actual != expected:
        raise ValueError("Frozen authority or accepted receipt bytes changed: " + path)
    value = json.loads(raw)
    if type(value) is not dict:
        raise ValueError("Frozen authority must be a JSON object")
    return value


def _expected(stage: Mapping[str, Any], master: Mapping[str, Any],
              primary: Mapping[str, Any], source: Mapping[str, Any],
              checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the one allowed review candidate, not a production executor."""
    if (master["hard_gate"]["stage10_execution_permitted"] is not False
        or master["stage10_treatment_outcomes_accessed"] is not False
        or stage["stage10_treatment_execution_authorized"] is not False
        or stage["stage10_treatment_outcomes_accessed_during_freeze"] is not False):
        raise ValueError("Frozen execution/outcome HOLD has changed")
    if (len(master["master_obligations"]) != 16
        or len(master["stage_specific_pre_outcome_freeze_required"]) != 19
        or stage["scenario"]["boundary_role"] != "offline_evaluator_scoring_and_diagnostics_only"
        or stage["information_timing"]["label_latency_rows"] != 5000
        or stage["information_timing"]["prediction_before_label_release"] is not True
        or stage["inherited_identities"]["seeds"] != [0, 1, 2, 3, 4]
        or stage["primary_arms"] != ["c_frozen_symbolic", "d_drift", "d_periodic"]
        or primary["execution"]["arms"] != stage["primary_arms"]
        or primary["execution"]["phase_order"] != [
            "phase_a_shared_control_plane", "phase_b_symbolic_arms",
            "phase_c_offline_evaluation"]):
        raise ValueError("Frozen scientific structure or matched Phase ordering diverges")
    row_count = int(stage["scenario"]["pre"]["rows"]) + int(stage["scenario"]["post"]["rows"])
    latency = int(stage["information_timing"]["label_latency_rows"])
    if (row_count != 138530 or source.get("pass") is not True
        or source.get("logical_rows") != row_count
        or source.get("frozen_features") != 77
        or source.get("label_latency_rows") != latency
        or source.get("raw_source_sha256") != stage["raw_source"]["sha256"]
        or source.get("ordered_row_ids_sha256") != stage["scenario"]["stream_row_ids_sha256"]
        or source.get("model_checkpoints_loaded") is not False
        or source.get("neural_or_symbolic_treatments_executed") is not False
        or checkpoint.get("pass") is not True
        or checkpoint.get("no_model_loaded_or_predicted") is not True
        or checkpoint.get("source_receipt_canonical_sha256") != source["canonical_sha256"]
        or [item["seed"] for item in checkpoint["checkpoint_files"]] != [0, 1, 2, 3, 4]):
        raise ValueError("Accepted original-source/checkpoint identity inconsistency")
    if primary["execution"]["phase_a_must_freeze_before_phase_b"] is not True:
        raise ValueError("Inherited Phase-A/Phase-B sealing rule changed")
    if primary["execution"]["write_once_outputs"] is not True:
        raise ValueError("Inherited write-once rule changed")
    return {
        "schema_version": 1,
        "candidate_id": "stage10a-production-schema-review-v0.1",
        "role": "WARM_non_governing_design_candidate",
        "status": "PROPOSAL_UNREVIEWED_NONEXECUTABLE",
        "frozen_authority_bytes": {k: v for k, (_, v) in PINNED.items()},
        "scientific_scope": {
            "scenario_id": stage["scenario_id"],
            "original_source_sha256": stage["raw_source"]["sha256"],
            "ordered_row_ids_sha256": stage["scenario"]["stream_row_ids_sha256"],
            "retained_rows": row_count,
            "pre_rows": int(stage["scenario"]["pre"]["rows"]),
            "post_rows": int(stage["scenario"]["post"]["rows"]),
            "original_features": int(source["frozen_features"]),
            "seeds": stage["inherited_identities"]["seeds"],
            "arms": stage["primary_arms"],
            "latency_rows": latency,
            "within_stream_mature_labels": row_count - latency,
            "right_censored_labels": latency,
            "boundary_evaluator_only": True,
            "inherited_preprocessing_sha256": stage["inherited_identities"]["preprocessing_core_state_sha256"],
            "inherited_r0_manifest_sha256": stage["inherited_identities"]["r0_v2_manifest_sha256"],
        },
        "layout_reuse": {
            "phase_a_dir": "phase_a_shared_control_plane/seed-{seed}",
            "phase_a_six_journals": list(PHASE_A_STREAMS),
            "phase_a_extra_candidate_artifacts": [
                "attempt.json", "input_identity.json", "runtime_attestation.json",
                "checkpoint_custody_receipt.json", "append_witness.jsonl",
                "shared_identity.json", "run_manifest.json", "stage10a_provenance_seal.json",
            ],
            "phase_b_dir": "phase_b_symbolic_arms/seed-{seed}",
            "phase_b_three_readonly_arms": stage["primary_arms"],
            "all_five_phase_a_seals_required_before_any_phase_b": True,
            "phase_c_offline_only_after_seals": True,
            "phase_a_and_child_checkpoints_read_only_to_arms": True,
        },
        "required_event_invariants": {
            "prediction_append_and_fsync_before_current_clock_label_release": True,
            "label_release_origin_equals_clock_minus_latency": True,
            "no_lookahead_labels_in_prediction_or_monitor_inputs": True,
            "no_boundary_or_pre_post_flag_in_adaptive_or_symbolic_inputs": True,
            "neural_checkpoint_publication_effective_next_row": True,
            "neural_monitor_uses_neural_hard_error_not_fused_arm_score": True,
            "immutable_rng_optimizer_replay_and_checkpoint_parent_child_custody": True,
            "all_attempts_failures_and_incomplete_seeds_retained": True,
        },
        "unresolved_review_choices": {
            "runtime_identity_external_witness": {
                "status": "PENDING_EXPLICIT_DESIGN_REVIEW",
                "option": "clean_exact_head_python3119_lock_plus_independent_runner_job_witness",
                "must_prove_outside_writer": True,
                "github_sha_self_report_alone_insufficient": True,
            },
            "label_availability_access_control": {
                "status": "PENDING_EXPLICIT_DESIGN_REVIEW",
                "option": "separate_process_or_equivalently_enforced_label_escrow",
                "must_preserve_frozen_neural_semantics": True,
                "same_process_fixture_is_not_production_proof": True,
            },
            "checkpoint_and_phase_b_custody": {
                "status": "PENDING_EXPLICIT_DESIGN_REVIEW",
                "option": "protected_raw_initial_child_bytes_and_readonly_model_resolver",
                "no_public_checkpoint_binaries_or_signed_links": True,
                "independent_byte_and_state_chain_verification_required": True,
            },
            "s10_04_release_scope": {
                "status": "PENDING_EXPLICIT_DESIGN_REVIEW",
                "criteria_frozen_not_second_dataset_selected": True,
                "external_replication_not_claimed": True,
                "do_not_weaken_master_obligations": True,
            },
        },
        "governance": {
            "stage10_execution_permitted": False,
            "stage10a_treatment_execution_authorized": False,
            "real_runtime_attested": False,
            "real_neural_trajectory_verified": False,
            "production_schema_frozen": False,
            "release_signed": False,
            "outcome_access_authorized": False,
            "real_stage10a_entrypoint_exists": False,
        },
    }


def assess_candidate(candidate: Mapping[str, Any], stage: Mapping[str, Any],
                     master: Mapping[str, Any], primary: Mapping[str, Any],
                     source: Mapping[str, Any], checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    if candidate != _expected(stage, master, primary, source, checkpoint):
        raise ValueError("Stage-10A production REVIEW candidate mismatches frozen authority or HOLD")
    return {
        "review_candidate_consistent": True,
        "source_and_original_checkpoint_receipt_identity_consistent": True,
        "outstanding_decisions": list(candidate["unresolved_review_choices"]),
        "production_schema_frozen": False,
        "production_runtime_verified": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
    }


def assess_repository(root: Path = ROOT) -> dict[str, Any]:
    documents = [_read_pinned(root, path) for path in PINNED]
    master, stage, primary, source, checkpoint = documents
    candidate_path = root / CANDIDATE
    if candidate_path.is_symlink() or not candidate_path.is_file():
        raise ValueError("Missing or redirected non-executable review candidate")
    candidate = json.loads(candidate_path.read_bytes())
    if type(candidate) is not dict:
        raise ValueError("Review candidate must be a JSON object")
    return assess_candidate(candidate, stage, master, primary, source, checkpoint)


if __name__ == "__main__":
    print(json.dumps(assess_repository(), sort_keys=True))
