from __future__ import annotations

import json

import pytest

from concept_drift_ids.cd_evidence import (
    CONTROL_PLANE_SCHEMA_VERSION,
    build_checkpoint_record,
    build_event,
    build_run_manifest,
    build_shared_identity,
    read_jsonl,
    records_sha256,
    verify_checkpoint_chain,
    verify_manifest_files,
    write_jsonl_new,
)


def test_event_builder_hashes_valid_event() -> None:
    event = build_event(
        run_id="run-1",
        seed=0,
        event_type="prediction",
        event_id="p-1",
        logical_clock=7,
        status="committed",
        origin_index=7,
        neural_checkpoint_sha256="abc",
        payload={"score": 0.5},
    )
    assert event["schema_version"] == CONTROL_PLANE_SCHEMA_VERSION
    assert len(event["event_sha256"]) == 64


def test_event_builder_rejects_boundary_metadata() -> None:
    with pytest.raises(ValueError, match="boundary"):
        build_event(
            run_id="run-1",
            seed=0,
            event_type="prediction",
            event_id="p-1",
            logical_clock=7,
            status="committed",
            payload={"boundary_flag": True},
        )


def test_jsonl_writer_is_write_once_and_round_trips(tmp_path) -> None:
    records = [
        build_event(
            run_id="run-1",
            seed=0,
            event_type="prediction",
            event_id=f"p-{i}",
            logical_clock=i,
            status="committed",
            origin_index=i,
        )
        for i in range(3)
    ]
    path = tmp_path / "events.jsonl"
    digest = write_jsonl_new(path, records)
    assert len(digest) == 64
    assert read_jsonl(path) == records
    with pytest.raises(FileExistsError, match="overwrite"):
        write_jsonl_new(path, records)


def test_checkpoint_chain_verifier_requires_exact_parent_lineage() -> None:
    root = build_checkpoint_record(
        sequence=0,
        parent_state_sha256=None,
        child_state_sha256="a",
        checkpoint_file_sha256="fa",
        event_id="initial",
        evidence_sha256="e0",
        config_sha256="c0",
        publication_effective_index=0,
    )
    child = build_checkpoint_record(
        sequence=1,
        parent_state_sha256="a",
        child_state_sha256="b",
        checkpoint_file_sha256="fb",
        event_id="drift-1",
        evidence_sha256="e1",
        config_sha256="c1",
        publication_effective_index=10,
    )
    verify_checkpoint_chain([root, child])

    bad = dict(child, parent_state_sha256="wrong")
    with pytest.raises(ValueError, match="parent"):
        verify_checkpoint_chain([root, bad])


def test_shared_identity_is_sensitive_to_each_component() -> None:
    base = build_shared_identity(
        label_schedule_sha256="a",
        detector_events_sha256="b",
        replay_evidence_sha256="c",
        checkpoint_chain_sha256="d",
    )
    changed = build_shared_identity(
        label_schedule_sha256="a",
        detector_events_sha256="b",
        replay_evidence_sha256="different",
        checkpoint_chain_sha256="d",
    )
    assert base["identity_sha256"] != changed["identity_sha256"]


def test_manifest_file_verifier_detects_corruption(tmp_path) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("frozen\n", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = build_run_manifest(
        run_id="run-1",
        seed=0,
        git_commit="deadbeef",
        protocol_hashes={"timing": "t"},
        runtime={"python_version": "3.11.9"},
        scenario_identity={"scenario_id": "toy"},
        initial_checkpoint_sha256="initial",
        preprocessing_sha256="pre",
        files={"artifact": {"path": "artifact.txt", "sha256": digest}},
        status="complete",
    )
    verify_manifest_files(tmp_path, manifest)
    artifact.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_manifest_files(tmp_path, manifest)


def test_records_hash_preserves_order() -> None:
    left = [{"x": 1}, {"x": 2}]
    right = [{"x": 2}, {"x": 1}]
    assert records_sha256(left) != records_sha256(right)
