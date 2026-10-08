from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from concept_drift_ids.cd_control_plane import (
    assert_no_boundary_contamination,
    canonical_sha256,
)
from concept_drift_ids.scenario_manifest import sha256_file


CONTROL_PLANE_SCHEMA_VERSION = 1

COMMON_EVENT_FIELDS = (
    "schema_version",
    "run_id",
    "seed",
    "arm",
    "event_type",
    "event_id",
    "logical_clock",
    "status",
)


def build_event(
    *,
    run_id: str,
    seed: int,
    event_type: str,
    event_id: str,
    logical_clock: int,
    status: str,
    arm: str = "shared_control_plane",
    origin_index: int | None = None,
    maturity_index: int | None = None,
    parent_event_id: str | None = None,
    neural_checkpoint_sha256: str | None = None,
    evidence_sha256: str | None = None,
    config_sha256: str | None = None,
    git_commit: str | None = None,
    reason: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema_version": CONTROL_PLANE_SCHEMA_VERSION,
        "run_id": str(run_id),
        "seed": int(seed),
        "arm": str(arm),
        "event_type": str(event_type),
        "event_id": str(event_id),
        "logical_clock": int(logical_clock),
        "status": str(status),
    }
    optional = {
        "origin_index": origin_index,
        "maturity_index": maturity_index,
        "parent_event_id": parent_event_id,
        "neural_checkpoint_sha256": neural_checkpoint_sha256,
        "evidence_sha256": evidence_sha256,
        "config_sha256": config_sha256,
        "git_commit": git_commit,
        "reason": reason,
    }
    event.update({key: value for key, value in optional.items() if value is not None})
    if payload:
        event["payload"] = dict(payload)
    validate_event(event)
    event["event_sha256"] = canonical_sha256(event)
    return event


def validate_event(event: Mapping[str, Any]) -> None:
    missing = [field for field in COMMON_EVENT_FIELDS if field not in event]
    if missing:
        raise ValueError(f"Event missing required fields: {missing}")
    if int(event["schema_version"]) != CONTROL_PLANE_SCHEMA_VERSION:
        raise ValueError("Unsupported control-plane event schema version.")
    if int(event["logical_clock"]) < 0:
        raise ValueError("logical_clock must be non-negative")
    origin = event.get("origin_index")
    maturity = event.get("maturity_index")
    if origin is not None and int(origin) > int(event["logical_clock"]):
        raise ValueError("Event uses an observation before its arrival.")
    if maturity is not None and int(maturity) < int(origin or 0):
        raise ValueError("maturity_index cannot precede origin_index.")
    assert_no_boundary_contamination(event)


def records_sha256(records: Iterable[Mapping[str, Any]]) -> str:
    return canonical_sha256(list(records))


def write_jsonl_new(
    path: Path,
    records: Sequence[Mapping[str, Any]],
    *,
    validate: bool = True,
) -> str:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as file:
        for record in records:
            if validate:
                validate_event(record)
            file.write(
                json.dumps(
                    dict(record),
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )
    return sha256_file(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_checkpoint_record(
    *,
    sequence: int,
    parent_state_sha256: str | None,
    child_state_sha256: str,
    checkpoint_file_sha256: str,
    event_id: str,
    evidence_sha256: str,
    config_sha256: str,
    publication_effective_index: int,
) -> dict[str, Any]:
    record = {
        "schema_version": CONTROL_PLANE_SCHEMA_VERSION,
        "sequence": int(sequence),
        "parent_state_sha256": parent_state_sha256,
        "child_state_sha256": str(child_state_sha256),
        "checkpoint_file_sha256": str(checkpoint_file_sha256),
        "event_id": str(event_id),
        "evidence_sha256": str(evidence_sha256),
        "config_sha256": str(config_sha256),
        "publication_effective_index": int(publication_effective_index),
    }
    record["record_sha256"] = canonical_sha256(record)
    return record


def verify_checkpoint_chain(records: Sequence[Mapping[str, Any]]) -> None:
    previous: str | None = None
    for expected_sequence, record in enumerate(records):
        if int(record["sequence"]) != expected_sequence:
            raise ValueError("Checkpoint chain sequence is not contiguous.")
        parent = record.get("parent_state_sha256")
        if expected_sequence == 0:
            if parent is not None:
                raise ValueError("Initial checkpoint record must have no parent.")
        elif parent != previous:
            raise ValueError("Checkpoint chain parent hash mismatch.")
        previous = str(record["child_state_sha256"])


def build_shared_identity(
    *,
    label_schedule_sha256: str,
    detector_events_sha256: str,
    replay_evidence_sha256: str,
    checkpoint_chain_sha256: str,
) -> dict[str, str]:
    identity = {
        "label_schedule_sha256": str(label_schedule_sha256),
        "detector_events_sha256": str(detector_events_sha256),
        "replay_evidence_sha256": str(replay_evidence_sha256),
        "checkpoint_chain_sha256": str(checkpoint_chain_sha256),
    }
    identity["identity_sha256"] = canonical_sha256(identity)
    return identity


def build_run_manifest(
    *,
    run_id: str,
    seed: int,
    git_commit: str,
    protocol_hashes: Mapping[str, str],
    runtime: Mapping[str, Any],
    scenario_identity: Mapping[str, Any],
    initial_checkpoint_sha256: str,
    preprocessing_sha256: str,
    files: Mapping[str, Mapping[str, str]],
    status: str,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": CONTROL_PLANE_SCHEMA_VERSION,
        "run_id": str(run_id),
        "seed": int(seed),
        "arm": "shared_control_plane",
        "git_commit": str(git_commit),
        "protocol_hashes": dict(protocol_hashes),
        "runtime": dict(runtime),
        "scenario_identity": dict(scenario_identity),
        "initial_checkpoint_sha256": str(initial_checkpoint_sha256),
        "preprocessing_sha256": str(preprocessing_sha256),
        "files": {key: dict(value) for key, value in files.items()},
        "status": str(status),
    }
    assert_no_boundary_contamination(
        {
            "protocol_hashes": manifest["protocol_hashes"],
            "runtime": manifest["runtime"],
        }
    )
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def verify_manifest_files(
    root: Path,
    manifest: Mapping[str, Any],
) -> None:
    for name, descriptor in manifest["files"].items():
        path = root / str(descriptor["path"])
        if not path.is_file():
            raise FileNotFoundError(f"Missing manifest file {name}: {path}")
        actual = sha256_file(path)
        expected = str(descriptor["sha256"])
        if actual != expected:
            raise ValueError(
                f"Manifest file hash mismatch for {name}: "
                f"expected {expected}, got {actual}"
            )
