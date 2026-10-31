"""Independent, read-only synthetic process-escrow artifact consistency verifier.

Cannot authenticate PIDs, filesystem durability, OS access controls, model
states, external trust, or Stage-10A treatment release.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "stage10a-process-escrow-synthetic-v1"
LATENCY = 5_000
SEEDS = tuple(range(5))
ZERO = "0" * 64


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _doc(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or redirected synthetic artifact")
    raw = path.read_bytes()
    try:
        obj = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Invalid synthetic JSON") from exc
    if type(obj) is not dict or raw != canonical(obj) + b"\n":
        raise ValueError("Noncanonical synthetic JSON")
    return obj


def _journal(path: Path) -> tuple[list[dict], bytes]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or redirected synthetic journal")
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("Truncated synthetic journal")
    items = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise ValueError("Malformed synthetic journal line") from exc
        if type(item) is not dict or canonical(item) != line:
            raise ValueError("Noncanonical synthetic journal line")
        items.append(item)
    return items, raw


def audit_seed(root: Path, seed: int, rows: int = LATENCY + 1) -> dict[str, Any]:
    if (type(seed) is not int or seed not in SEEDS or type(rows) is not int
        or rows not in (LATENCY + 1, LATENCY + 2)):
        raise ValueError("Only bounded five-seed synthetic fixtures accepted")
    d = Path(root) / f"seed-{seed}"
    if d.is_symlink() or not d.is_dir() or {p.name for p in d.iterdir()} != {
        "attempt.json", "predictions.jsonl", "escrow_receipts.jsonl", "seal.json"
    }:
        raise ValueError("Synthetic artifact inventory must be exact and complete")
    attempt = _doc(d / "attempt.json")
    writer_pid = attempt.get("writer_pid")
    if (type(writer_pid) is not int or writer_pid <= 0 or attempt != {
        "schema": SCHEMA, "seed": seed, "rows": rows, "writer_pid": writer_pid,
        "fixture_only": True, "model_loaded": False,
        "stage10a_treatment_execution_authorized": False
    }):
        raise ValueError("Invalid synthetic writer attempt/release claim")
    predictions, pred_raw = _journal(d / "predictions.jsonl")
    receipts, receipt_raw = _journal(d / "escrow_receipts.jsonl")
    if len(predictions) != rows or len(receipts) != rows:
        raise ValueError("Incomplete synthetic prediction/escrow chronology")
    previous = ZERO
    observed_pid = None
    for clock in range(rows):
        core = {"schema": SCHEMA, "seed": seed, "kind": "prediction_commit",
                "clock": clock, "origin_index": clock,
                "row_id": f"synthetic:seed-{seed}:row-{clock}",
                "maturity_index": clock + LATENCY,
                "fake_prediction_sha256": sha(f"{SCHEMA}|neural-fixture-token|{seed}|{clock}".encode()),
                "previous_prediction_sha256": previous}
        current = sha(canonical(core))
        if predictions[clock] != {**core, "record_sha256": current}:
            raise ValueError("Synthetic prediction order, hash chain or boundary leak")
        origin = clock - LATENCY
        pid = receipts[clock].get("escrow_pid")
        if type(pid) is not int or pid <= 0 or pid == writer_pid:
            raise ValueError("Unverified or same-PID escrow receipt")
        if observed_pid is None:
            observed_pid = pid
        expected_receipt = {"schema": SCHEMA, "seed": seed, "clock": clock,
                            "prediction_sha256": current, "escrow_pid": observed_pid,
                            "mature_label_origin": origin if origin >= 0 else None,
                            "mature_label": (seed + 7*origin)%2 if origin >= 0 else None}
        if receipts[clock] != expected_receipt:
            raise ValueError("Synthetic escrow receipt does not match committed prediction or maturity")
        previous = current
    seal = _doc(d / "seal.json")
    expected_seal = {"schema": SCHEMA, "seed": seed, "rows": rows,
                     "prediction_sha256": sha(pred_raw),
                     "escrow_receipts_sha256": sha(receipt_raw),
                     "last_prediction_sha256": previous,
                     "writer_pid": writer_pid, "escrow_pid": observed_pid,
                     "fixture_only": True, "same_user_processes_not_an_access_boundary": True,
                     "external_runtime_attested": False, "real_durable_fsync_attested": False,
                     "real_process_access_controls_verified": False,
                     "real_neural_state_verified": False, "release_signed": False,
                     "stage10a_treatment_execution_authorized": False}
    if seal != expected_seal:
        raise ValueError("Synthetic seal changed or unauthorized production claim")
    return {"seed": seed, "cross_process_fixture_verified": True,
            "prediction_rows": rows, "within_stream_mature_labels": rows-LATENCY,
            "production_isolation_verified": False,
            "stage10a_treatment_execution_authorized": False}


def audit_all(root: Path, rows: int = LATENCY + 1) -> dict[str, Any]:
    if type(rows) is not int or rows not in (LATENCY+1, LATENCY+2):
        raise ValueError("Non-synthetic row count refused")
    r = Path(root)
    if r.is_symlink() or not r.is_dir() or {p.name for p in r.iterdir()} != {
        f"seed-{seed}" for seed in SEEDS
    }:
        raise ValueError("Missing or substituted frozen five-seed fixture")
    states = [audit_seed(r, seed, rows) for seed in SEEDS]
    return {"cross_process_synthetic_only_pass": True,
            "five_seeds": [item["seed"] for item in states],
            "production_durable_journal_verified": False,
            "production_label_confidentiality_verified": False,
            "production_runtime_trust_verified": False,
            "stage10a_treatment_execution_authorized": False,
            "stage10a_release_ready": False}
