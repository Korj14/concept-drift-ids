from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from concept_drift_ids.cd_control_plane import (
    canonical_sha256,
    write_json_new,
)
from concept_drift_ids.cd_symbolic_arms import (
    PendingSymbolicTransaction,
    SymbolicTransactionResult,
    ValidationBlockResult,
)
from concept_drift_ids.cd_symbolic_lifecycle import (
    RuleBaseState,
    verify_lifecycle_state,
)


SYMBOLIC_EVIDENCE_SCHEMA_VERSION = 1


def lifecycle_state_payload(state: RuleBaseState) -> dict[str, Any]:
    verify_lifecycle_state(state)
    return state.to_dict()


def maintenance_event_payload(
    *,
    run_id: str,
    seed: int,
    arm: str,
    transaction: PendingSymbolicTransaction,
    validation: ValidationBlockResult,
    result: SymbolicTransactionResult,
    parent_rule_base_version_id: str,
    parent_rule_base_sha256: str,
    git_commit: str,
) -> dict[str, Any]:
    lifecycle = result.lifecycle
    payload: dict[str, Any] = {
        "schema_version": SYMBOLIC_EVIDENCE_SCHEMA_VERSION,
        "run_id": str(run_id),
        "seed": int(seed),
        "arm": str(arm),
        "opportunity_id": int(transaction.opportunity_id),
        "opportunity_clock": int(transaction.opportunity_clock),
        "neural_checkpoint_sha256": transaction.neural_checkpoint_sha256,
        "checkpoint_publication_effective_index": (
            transaction.checkpoint_publication_effective_index
        ),
        "validation_start_index": transaction.validation_start_index,
        "generation_evidence_id": transaction.generation_evidence_id,
        "generation_row_ids_sha256": canonical_sha256(
            list(transaction.generation_row_ids)
        ),
        "operator_config_sha256": transaction.operator_config_sha256,
        "validation_status": validation.status,
        "validation_row_count": len(validation.records),
        "validation_row_ids_sha256": canonical_sha256(
            list(validation.row_ids)
        ),
        "maintenance_status": result.status,
        "parent_rule_base_version_id": str(parent_rule_base_version_id),
        "parent_rule_base_sha256": str(parent_rule_base_sha256),
        "git_commit": str(git_commit),
        "published": bool(lifecycle.published) if lifecycle is not None else False,
    }
    if lifecycle is not None:
        payload["staleness_snapshot"] = list(lifecycle.staleness_snapshot)
        payload["candidate_evidence"] = list(lifecycle.candidate_evidence)
        payload["decisions"] = list(lifecycle.decisions)
        payload["result_rule_base_version_id"] = (
            lifecycle.state.rule_base_version_id
        )
        payload["result_rule_base_sha256"] = lifecycle.state.canonical_sha256
        payload["result_history_sha256"] = lifecycle.state.history_sha256
    payload["maintenance_event_sha256"] = canonical_sha256(payload)
    return payload


def rule_base_version_payload(
    state: RuleBaseState,
    *,
    maintenance_event_sha256: str,
    neural_checkpoint_sha256: str,
    valid_from: int,
    git_commit: str,
) -> dict[str, Any]:
    verify_lifecycle_state(state)
    if state.version_number <= 0:
        raise ValueError(
            "Initial migrated R0.v2 state is not a D publication artifact."
        )
    payload = {
        "schema_version": SYMBOLIC_EVIDENCE_SCHEMA_VERSION,
        "seed": state.seed,
        "rule_base_version_id": state.rule_base_version_id,
        "version_number": state.version_number,
        "parent_rule_base_version_id": state.parent_version_id,
        "parent_rule_base_sha256": state.parent_version_sha256,
        "maintenance_event_sha256": str(maintenance_event_sha256),
        "neural_checkpoint_sha256": str(neural_checkpoint_sha256),
        "valid_from": int(valid_from),
        "active_revision_ids": list(state.active_revision_ids),
        "canonical_rule_base_sha256": state.canonical_sha256,
        "lifecycle_history_sha256": state.history_sha256,
        "state": lifecycle_state_payload(state),
        "git_commit": str(git_commit),
    }
    payload["version_artifact_sha256"] = canonical_sha256(payload)
    return payload


def write_symbolic_maintenance_new(
    output_dir: Path,
    *,
    run_id: str,
    seed: int,
    arm: str,
    transaction: PendingSymbolicTransaction,
    validation: ValidationBlockResult,
    result: SymbolicTransactionResult,
    parent_state: RuleBaseState,
    git_commit: str,
    publication_effective_index: int | None,
) -> dict[str, Mapping[str, str]]:
    output_dir = Path(output_dir)
    opportunity_dir = (
        output_dir
        / f"seed-{seed}"
        / str(arm)
        / f"opportunity-{transaction.opportunity_id:04d}"
    )
    event = maintenance_event_payload(
        run_id=run_id,
        seed=seed,
        arm=arm,
        transaction=transaction,
        validation=validation,
        result=result,
        parent_rule_base_version_id=parent_state.rule_base_version_id,
        parent_rule_base_sha256=parent_state.canonical_sha256,
        git_commit=git_commit,
    )
    event_path = opportunity_dir / "maintenance_event.json"
    event_file_sha = write_json_new(event_path, event)
    out: dict[str, Mapping[str, str]] = {
        "maintenance_event": {
            "path": str(event_path),
            "sha256": event_file_sha,
            "payload_sha256": event["maintenance_event_sha256"],
        }
    }

    if result.lifecycle is not None and result.lifecycle.published:
        if publication_effective_index is None:
            raise ValueError(
                "Published symbolic state requires an effective logical index."
            )
        version = rule_base_version_payload(
            result.lifecycle.state,
            maintenance_event_sha256=event["maintenance_event_sha256"],
            neural_checkpoint_sha256=transaction.neural_checkpoint_sha256,
            valid_from=publication_effective_index,
            git_commit=git_commit,
        )
        version_path = (
            output_dir
            / f"seed-{seed}"
            / str(arm)
            / "versions"
            / f"{result.lifecycle.state.rule_base_version_id}.json"
        )
        version_file_sha = write_json_new(version_path, version)
        out["rule_base_version"] = {
            "path": str(version_path),
            "sha256": version_file_sha,
            "payload_sha256": version["version_artifact_sha256"],
        }
    return out


def verify_version_parent_chain(
    versions: list[Mapping[str, Any]],
) -> None:
    ordered = sorted(
        versions,
        key=lambda item: int(item["version_number"]),
    )
    previous_id: str | None = None
    previous_hash: str | None = None
    for expected, item in enumerate(ordered, start=1):
        if int(item["version_number"]) != expected:
            raise ValueError("Symbolic version numbers are not contiguous.")
        if expected == 1:
            if item["parent_rule_base_version_id"] is None:
                raise ValueError("First D version must reference migrated R0.v2.")
        else:
            if item["parent_rule_base_version_id"] != previous_id:
                raise ValueError("Symbolic rule-base parent version mismatch.")
            if item["parent_rule_base_sha256"] != previous_hash:
                raise ValueError("Symbolic rule-base parent hash mismatch.")
        previous_id = str(item["rule_base_version_id"])
        previous_hash = str(item["canonical_rule_base_sha256"])
