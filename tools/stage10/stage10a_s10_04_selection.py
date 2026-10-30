"""Stage-10A/S10-04 independent second-environment eligibility, source-only.

Never observes network records, model outcomes, or scores. Does NOT select
or rank real datasets. This is a prospective gate over supplied synthetic
candidate *metadata* only; no C/D scientific execution is permitted.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "data/manifests/stage10a_s10_04_independent_environment_eligibility_v1.json"
MASTER_PATH = ROOT / "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json"
STAGE10A_PATH = ROOT / "data/manifests/stage10a_goldeneye_attack_pattern_v1.json"

REQUIRED_SOURCE_DOSSIER = frozenset({
    "candidate_id",
    "independent_collection",
    "materially_different_environment",
    "flow_oriented_source",
    "original_source_provenance_verifiable",
    "legitimate_access",
    "attack_benign_label_mapping_precommitted",
    "chronology_defined_prospectively",
    "leakage_safe_partitions_frozen",
    "feature_semantics_reconstructible",
    "symbolic_semantics_reconstructible_without_distortion",
    "cicids2017_derived_or_relabelled",
    "same_traffic_capture_as_cicids2017",
    "treatment_outcomes_consulted",
})
YES_FIELDS = frozenset({
    "independent_collection",
    "materially_different_environment",
    "flow_oriented_source",
    "original_source_provenance_verifiable",
    "legitimate_access",
    "attack_benign_label_mapping_precommitted",
    "chronology_defined_prospectively",
    "leakage_safe_partitions_frozen",
    "feature_semantics_reconstructible",
    "symbolic_semantics_reconstructible_without_distortion",
})
NO_FIELDS = frozenset({
    "cicids2017_derived_or_relabelled",
    "same_traffic_capture_as_cicids2017",
    "treatment_outcomes_consulted",
})


def verify_policy(
    policy: Mapping[str, Any],
    master: Mapping[str, Any],
    stage10a: Mapping[str, Any],
) -> None:
    if not (master["hard_gate"]["stage10_execution_permitted"] is False
            and stage10a["stage10_treatment_execution_authorized"] is False
            and stage10a["stage10_treatment_outcomes_accessed_during_freeze"] is False):
        raise ValueError("Frozen Stage-10/10A treatment firewall is open.")
    obligations = {entry["id"]: entry for entry in master["master_obligations"]}
    if (len(master["master_obligations"]) != 16
        or len(master["stage_specific_pre_outcome_freeze_required"]) != 19
        or obligations["S10-04"]["type"] != "external_replication"):
        raise ValueError("Governing master S10-04 contract changed.")
    if (policy["id"] != "stage10a-s10-04-independent-environment-eligibility-v1"
        or policy["governing_master"]["git_blob_sha1"]
        != "ac61908d30bcc26cddbe6467d807a3de119689d9"
        or policy["stage10a_context"]["original_protocol_git_blob_sha1"]
        != "2785e94380cc29e20f014738e2837d708649f5bc"
        or policy["stage10a_context"]["scenario_id"] != stage10a["scenario_id"]):
        raise ValueError("S10-04 criteria authority drift.")
    selection = policy["selection"]
    if (selection["selected_dataset_id"] is not None
        or selection["candidates_assessed"] != 0
        or selection["second_dataset_chosen"] is not False
        or selection["outcome_guided_choice_permitted"] is not False
        or selection["independent_external_replication_claim_permitted"] is not False
        or selection["selection_completion_status"] != "HOLD"):
        raise ValueError("S10-04 criteria record must not assert dataset selection.")
    if any(value is not True for value in policy["selection_assessment_requirements"].values()):
        raise ValueError("S10-04 prospective selection criteria weakened.")
    if any(value is not True for value in policy["causal_reporting"].values()):
        raise ValueError("S10-04 causal/reporting safeguards weakened.")
    if (policy["safety"]["treatment_release"] is not False
        or policy["safety"]["stage10a_treatment_outcomes_accessed"] is not False
        or policy["safety"]["gate_closed_even_if_eligibility_rules_frozen"] is not True):
        raise ValueError("S10-04 criteria are not a treatment release.")
    if (len(policy["necessary_inclusion_rules"]) != 8
        or len(policy["hard_exclusions"]) != 7
        or len(set(policy["necessary_inclusion_rules"])) != 8
        or len(set(policy["hard_exclusions"])) != 7):
        raise ValueError("Selection rule set is missing or duplicated.")


def screen_synthetic_dossier(dossier: Mapping[str, Any]) -> dict[str, Any]:
    """Pure, fail-closed gate over explicit *synthetic metadata* only.

    A positive result means 'source screening criteria met', NEVER an actual
    selected dataset, an empirical fact about a real dataset, or release.
    """
    if set(dossier) != REQUIRED_SOURCE_DOSSIER:
        raise ValueError("Source dossier schema mismatch or unauthorized outcome field.")
    if not isinstance(dossier["candidate_id"], str) or not dossier["candidate_id"].strip():
        raise ValueError("Candidate metadata identity required.")
    if any(type(dossier[k]) is not bool for k in YES_FIELDS | NO_FIELDS):
        raise ValueError("Every evidence gate requires an explicit boolean.")
    reasons = tuple(
        sorted([key for key in YES_FIELDS if dossier[key] is False]
               + [key for key in NO_FIELDS if dossier[key] is True])
    )
    return {
        "source_eligibility_pass": not reasons,
        "failed_source_fields": list(reasons),
        "treatment_outcomes_consulted": dossier["treatment_outcomes_consulted"],
        "independent_environment_replication_demonstrated": False,
        "candidate_selected": False,
        "stage10a_treatment_execution_authorized": False,
    }


def verify_repository_policy() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    stage10a = json.loads(STAGE10A_PATH.read_text(encoding="utf-8"))
    verify_policy(policy, master, stage10a)


if __name__ == "__main__":
    verify_repository_policy()
    print(json.dumps({
        "s10_04_criteria_valid": True,
        "second_dataset_selected": False,
        "treatment_authorized": False,
    }, sort_keys=True))
