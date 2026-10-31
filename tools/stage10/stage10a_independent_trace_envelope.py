"""Independent, read-only Stage-10A synthetic trace-envelope verifier.

A prospective envelope DESIGN proof only. Never verifies or executes a real
neural model. No import from the synthetic writer or any treatment module.
The real-trace schema and authoritative writer provenance still require review.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SEEDS = (0, 1, 2, 3, 4)
ARMS = ("c_frozen_symbolic", "d_drift", "d_periodic")
FIXTURE = "stage10a-shared-writer-synthetic-only-v1"
ENVELOPE_SCHEMA = "stage10a-independent-synthetic-trace-envelope-v1"
LATENCY = 5000
LOW = LATENCY + 1
HIGH = LATENCY + 3
MASTER_BLOB = "8ac82c8d907243556a5673d09600cd1bdc19aa52"
STAGE_BLOB = "001501350fbf9fa4a4075176b9af43c2cf275bc5"
SOURCE_RECEIPT_SHA = "d6e0874181b4aebe4d259b7f4f66b7d608aaf7803c6dc3c10f0151aaf2f9a42a"
CHECKPOINT_RECEIPT_SHA = "94cf6ee608e63be4834372aa0be8956eaaf289234f395dd788a9e0d23ba2b1c1"
RECEIPT_SOURCE = "results/audits/stage10a_original_source_receipt_601516ff_2026_10_31.json"
RECEIPT_CHECKPOINT = "results/audits/stage10a_original_checkpoint_source_only_receipt_41156553037.json"
ARTIFACT_FILES = ("attempt.json", "shared.jsonl", "sealed.json") + tuple(
    f"arm-{arm}.json" for arm in ARMS
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_line(doc: dict[str, Any]) -> bytes:
    return (json.dumps(doc, sort_keys=True, separators=(",", ":"),
                       allow_nan=False, ensure_ascii=False) + "\n").encode()


def _read_canonical(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing, redirected, or nonregular evidence file")
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Malformed immutable evidence JSON") from exc
    if type(document) is not dict or raw != _json_line(document):
        raise ValueError("Evidence JSON must be canonical with exact field types")
    return document


def _frozen_json(root: Path, rel: str, sha: str, *, git_blob: bool = False) -> dict:
    path = root / rel
    raw = path.read_bytes()
    actual = (hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
              if git_blob else _sha(raw))
    if actual != sha:
        raise ValueError("Original frozen authority/receipt bytes changed")
    return json.loads(raw)


def read_authorities(root: Path = ROOT) -> tuple[dict, dict]:
    """Recheck actual accepted source-only receipt bytes, not user assertions."""
    master = _frozen_json(root,
        "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json",
        MASTER_BLOB, git_blob=True)
    stage = _frozen_json(root,
        "data/manifests/stage10a_goldeneye_attack_pattern_v1.json",
        STAGE_BLOB, git_blob=True)
    sr = _frozen_json(root, RECEIPT_SOURCE, SOURCE_RECEIPT_SHA)
    cr = _frozen_json(root, RECEIPT_CHECKPOINT, CHECKPOINT_RECEIPT_SHA)
    if (master["hard_gate"]["stage10_execution_permitted"] is not False
        or master["stage10_treatment_outcomes_accessed"] is not False
        or stage["stage10_treatment_execution_authorized"] is not False
        or stage["stage10_treatment_outcomes_accessed_during_freeze"] is not False
        or sr["pass"] is not True or cr["pass"] is not True
        or sr["raw_source_sha256"] != stage["raw_source"]["sha256"]
        or cr["source_receipt_canonical_sha256"] != sr["canonical_sha256"]
        or cr["no_model_loaded_or_predicted"] is not True
        or cr["stage10a_treatment_execution_authorized"] is not False
        or len(cr["checkpoint_files"]) != 5
        or tuple(x["seed"] for x in cr["checkpoint_files"]) != SEEDS):
        raise ValueError("Frozen source-only or scientific HOLD authority mismatch")
    return stage, cr


def _prediction(seed: int, i: int) -> dict[str, Any]:
    return {"event_type": "prediction", "logical_clock": i, "origin_index": i,
            "prediction_committed": True,
            "synthetic_neural_token_sha256": _sha(
                f"{FIXTURE}|seed={seed}|origin={i}|neural".encode())}


def _mature_label(seed: int, clock: int) -> dict[str, Any]:
    return {"event_type": "label_release", "logical_clock": clock,
            "origin_index": clock - LATENCY, "maturity_index": clock,
            "synthetic_binary_label": (seed + clock - LATENCY) % 2}


def expected_envelope(seed: int, count: int, sha_by_file: dict[str, str],
                      stage: dict, original: dict) -> dict[str, Any]:
    """Pure expected schema used by an independent byte auditor; never release."""
    if type(seed) is not int or seed not in SEEDS or type(count) is not int or not LOW <= count <= HIGH:
        raise ValueError("Only five frozen seeds and bounded synthetic fixtures")
    if set(sha_by_file) != set(ARTIFACT_FILES) or any(
        not isinstance(d, str) or re.fullmatch(r"[0-9a-f]{64}", d) is None
        for d in sha_by_file.values()
    ):
        raise ValueError("Synthetic artifact inventory is incomplete or malformed")
    return {
        "schema": ENVELOPE_SCHEMA, "scope": "synthetic_only_not_real_execution",
        "seed": seed, "logical_rows": count, "latency_rows": LATENCY,
        "source_receipt_raw_sha256": SOURCE_RECEIPT_SHA,
        "checkpoint_receipt_raw_sha256": CHECKPOINT_RECEIPT_SHA,
        "source_sha256": stage["raw_source"]["sha256"],
        "ordered_row_ids_sha256": stage["scenario"]["stream_row_ids_sha256"],
        "initial_checkpoint_sha256": original["checkpoint_files"][seed]["sha256"],
        "preprocessing_core_sha256": stage["inherited_identities"]["preprocessing_core_state_sha256"],
        "r0_v2_manifest_sha256": stage["inherited_identities"]["r0_v2_manifest_sha256"],
        "arms": list(ARMS), "shared_writer_count": 1,
        "artifacts_sha256": dict(sorted(sha_by_file.items())),
        "git_head_independently_authenticated": False,
        "neural_control_raw_state_independently_verified": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
    }


def audit_seed(root: Path, seed: int, count: int, stage: dict,
               original: dict) -> str:
    if type(seed) is not int or seed not in SEEDS or type(count) is not int or not LOW <= count <= HIGH:
        raise ValueError("Unsupported seed or non-synthetic count")
    path = root / f"seed-{seed}"
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Missing or redirected seed directory")
    if {p.name for p in path.iterdir()} != set(ARTIFACT_FILES) | {"trace_envelope.json"}:
        raise ValueError("Unexpected, missing or duplicate journal artifacts")
    for name in ARTIFACT_FILES:
        if (path / name).is_symlink() or not (path / name).is_file():
            raise ValueError("Unexpected symlink or missing artifact")
    if (path / "shared.jsonl").stat().st_size > 2_000_000:
        raise ValueError("Non-synthetic oversized trace")
    sha_by_file = {name: _sha((path / name).read_bytes()) for name in ARTIFACT_FILES}
    envelope = _read_canonical(path / "trace_envelope.json")
    if envelope != expected_envelope(seed, count, sha_by_file, stage, original):
        raise ValueError("Envelope does not match frozen source and actual raw bytes")
    attempt = _read_canonical(path / "attempt.json")
    if attempt != {"fixture": FIXTURE, "seed": seed, "count": count,
                   "writer_role": "single_shared_writer", "real_execution": False,
                   "stage10a_treatment_execution_authorized": False}:
        raise ValueError("Synthetic writer attempt identity diverged")
    observed = (path / "shared.jsonl").read_bytes().splitlines(keepends=True)
    if len(observed) != count + (count - LATENCY):
        raise ValueError("Missing or extraneous raw event")
    position = 0
    for clock in range(count):
        if observed[position] != _json_line(_prediction(seed, clock)):
            raise ValueError("Prediction evidence was changed, reordered, or leaked")
        position += 1
        if clock >= LATENCY:
            if observed[position] != _json_line(_mature_label(seed, clock)):
                raise ValueError("Premature, missing, altered or non-durable label event")
            position += 1
    raw_shared = (path / "shared.jsonl").read_bytes()
    seal = _read_canonical(path / "sealed.json")
    if seal != {"fixture": FIXTURE, "seed": seed, "count": count,
                "journal_sha256": _sha(raw_shared), "journal_bytes": len(raw_shared),
                "writer_role": "single_shared_writer", "real_execution": False,
                "stage10a_treatment_execution_authorized": False}:
        raise ValueError("Sealed single writer identity is not raw-byte backed")
    for arm in ARMS:
        binding = _read_canonical(path / f"arm-{arm}.json")
        expected = {
            "fixture": FIXTURE, "seed": seed, "arm": arm,
            "shared_journal_sha256": _sha(raw_shared),
            "shared_seal_sha256": sha_by_file["sealed.json"],
            "shared_writer_role": "read_only", "neural_writer_invocations": 0,
            "symbolic_fixture_token_sha256": _sha(
                f"{FIXTURE}|seed={seed}|arm={arm}|symbolic".encode()),
            "real_execution": False, "stage10a_treatment_execution_authorized": False,
        }
        if binding != expected:
            raise ValueError("Arm is not immutably bound to one shared writer")
    return _sha(raw_shared)


def audit_all(root: Path, *, count: int = LOW,
              repository_root: Path = ROOT) -> dict[str, Any]:
    """No real-mode branch exists. Does not verify a trusted runtime witness."""
    stage, original = read_authorities(repository_root)
    root = Path(root)
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != {
        f"seed-{seed}" for seed in SEEDS
    }:
        raise ValueError("Exactly five disjoint synthetic seed directories required")
    digests = {str(seed): audit_seed(root, seed, count, stage, original) for seed in SEEDS}
    if len(set(digests.values())) != len(SEEDS):
        raise ValueError("Independent synthetic seed traces were repeated")
    return {
        "scope": ENVELOPE_SCHEMA, "five_seed_envelopes_valid": True,
        "shared_raw_journal_sha256_by_seed": digests,
        "accepted_source_only_receipts_rechecked": True,
        "production_git_head_authenticated": False,
        "production_neural_checkpoint_chain_verified": False,
        "production_prediction_label_order_verified": False,
        "real_matched_three_arm_neural_execution_verified": False,
        "model_loaded_or_predicted": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
        "status": "HOLD_SYNTHETIC_SCHEMA_ONLY",
    }
