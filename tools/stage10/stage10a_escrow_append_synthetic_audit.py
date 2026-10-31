"""Independent, read-only consistency audit of bounded synthetic escrow events.

No model, fixture writer, runtime, dataset, or network imports. This cannot
independently witness a real fsync or grant a production-release decision.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "stage10a-escrow-append-synthetic-v1"
LATENCY = 5_000
SEEDS = tuple(range(5))
ZERO = "0" * 64


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_doc(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or redirected synthetic evidence")
    raw = path.read_bytes()
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid synthetic evidence JSON") from exc
    if type(doc) is not dict or raw != canonical(doc) + b"\n":
        raise ValueError("Noncanonical synthetic evidence JSON")
    return doc


def audit_seed(root: Path, seed: int, rows: int = LATENCY + 1) -> dict[str, Any]:
    if type(seed) is not int or seed not in SEEDS or type(rows) is not int or rows not in (LATENCY + 1, LATENCY + 2):
        raise ValueError("Only bounded synthetic seeds and rows may be verified")
    d = Path(root) / f"seed-{seed}"
    if d.is_symlink() or not d.is_dir():
        raise ValueError("Missing or redirected synthetic seed")
    if {p.name for p in d.iterdir()} != {"attempt.json", "events.jsonl", "seal.json"}:
        raise ValueError("Synthetic evidence inventory changed")
    attempt = _read_doc(d / "attempt.json")
    if attempt != {"schema": SCHEMA, "seed": seed, "rows": rows,
                   "fixture_only": True, "real_model_loaded": False,
                   "stage10a_treatment_execution_authorized": False}:
        raise ValueError("Synthetic attempt identity or release claim changed")
    journal = d / "events.jsonl"
    if journal.is_symlink():
        raise ValueError("Redirected event journal")
    raw = journal.read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("Truncated synthetic journal")
    observed = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Malformed synthetic event") from exc
        if type(item) is not dict or canonical(item) != line:
            raise ValueError("Noncanonical synthetic event")
        observed.append(item)
    expected = []
    prev = ZERO
    prediction_ids: dict[int, str] = {}
    for clock in range(rows):
        # Independent derivation of the synthetic prediction token (no writer import).
        token = sha256(f"{SCHEMA}:fake-neural-token:{seed}:{clock}".encode())
        bodies = [{
            "kind": "prediction_commit", "clock": clock, "origin_index": clock,
            "row_id": f"fixture:s{seed}:r{clock}",
            "maturity_index": clock + LATENCY,
            "fake_neural_token": token,
        }]
        for body in bodies:
            core = {**body, "schema": SCHEMA, "seed": seed,
                    "prev_sha256": prev}
            event_hash = sha256(canonical(core))
            expected.append({**core, "event_sha256": event_hash})
            prev = event_hash
            prediction_ids[clock] = event_hash
        if clock >= LATENCY:
            origin = clock - LATENCY
            body = {
                "kind": "mature_label_grant", "clock": clock,
                "origin_index": origin, "row_id": f"fixture:s{seed}:r{origin}",
                "maturity_index": clock, "true_label": (seed + 7*origin) % 2,
                "origin_prediction_event_sha256": prediction_ids[origin],
                "current_prediction_event_sha256": prediction_ids[clock],
            }
            core = {**body, "schema": SCHEMA, "seed": seed,
                    "prev_sha256": prev}
            event_hash = sha256(canonical(core))
            expected.append({**core, "event_sha256": event_hash})
            prev = event_hash
    if observed != expected:
        raise ValueError("Synthetic raw event, label maturity or chain altered")
    seal = _read_doc(d / "seal.json")
    target = {
        "schema": SCHEMA, "seed": seed, "rows": rows,
        "event_count": len(expected), "final_event_sha256": prev,
        "journal_sha256": sha256(raw), "fixture_only": True,
        "real_runtime_attested": False,
        "external_append_order_witnessed": False,
        "label_process_isolated": False,
        "real_neural_trajectory_verified": False,
        "stage10a_release_ready": False,
        "stage10a_treatment_execution_authorized": False,
    }
    if seal != target:
        raise ValueError("Synthetic seal mismatch or unauthorized promotion")
    return {"seed": seed, "fixture_verified": True,
            "event_count": len(expected),
            "production_order_and_isolation_verified": False,
            "stage10a_treatment_execution_authorized": False}


def audit_all(root: Path, rows: int = LATENCY + 1) -> dict[str, Any]:
    if type(rows) is not int or rows not in (LATENCY + 1, LATENCY + 2):
        raise ValueError("Only bounded synthetic row counts")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Missing synthetic root")
    if {p.name for p in root.iterdir()} != {f"seed-{s}" for s in SEEDS}:
        raise ValueError("Expected exactly five frozen synthetic seeds")
    results = [audit_seed(root, seed, rows) for seed in SEEDS]
    return {"fixture_only_pass": True, "seeds": [r["seed"] for r in results],
            "production_runtime_attested": False,
            "production_label_escrow_enforced": False,
            "stage10a_release_ready": False,
            "stage10a_treatment_execution_authorized": False}
