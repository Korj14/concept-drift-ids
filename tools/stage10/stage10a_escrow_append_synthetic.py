"""Stage-10A supplemental SYNTHETIC-ONLY append/escrow contract.

Not a production executor, an external fsync witness, hardware attestation,
model code, dataset loader, experiment, or treatment RELEASE. Bounded fixture
rows are exactly 5,001 or 5,002. No neural checkpoints or CICIDS files used.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

SCHEMA = "stage10a-escrow-append-synthetic-v1"
LATENCY = 5_000
ALLOWED_ROWS = (LATENCY + 1, LATENCY + 2)
SEEDS = tuple(range(5))
ZERO = "0" * 64


def canonical(doc: Any) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fake_prediction(seed: int, index: int) -> str:
    return digest(f"{SCHEMA}:fake-neural-token:{seed}:{index}".encode())


def fake_label(seed: int, index: int) -> int:
    return (seed + index * 7) % 2


def _valid(seed: int, rows: int) -> None:
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError("Only frozen seed IDs 0..4 are supported")
    if type(rows) is not int or rows not in ALLOWED_ROWS:
        raise ValueError("Synthetic fixture only; production row counts forbidden")


def _new_json(path: Path, doc: dict[str, Any]) -> None:
    with path.open("xb") as f:
        f.write(canonical(doc) + b"\n")
        f.flush()
        os.fsync(f.fileno())


class AppendWitness:
    """Same-process fixture journal; its fsync cannot attest an external runner."""

    def __init__(self, directory: Path, seed: int, rows: int):
        _valid(seed, rows)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.seed = seed
        self.rows = rows
        self.prev = ZERO
        self.next_clock = 0
        self.prediction_ids: dict[int, str] = {}
        self.durable_prediction_clock: int | None = None
        self.ack_count = 0
        self._closed = False
        _new_json(self.directory / "attempt.json", {
            "schema": SCHEMA, "seed": seed, "rows": rows,
            "fixture_only": True, "real_model_loaded": False,
            "stage10a_treatment_execution_authorized": False,
        })
        self._file = (self.directory / "events.jsonl").open("xb")

    def _append(self, doc: dict[str, Any]) -> str:
        if self._closed:
            raise RuntimeError("Sealed journal cannot be appended")
        body = {**doc, "schema": SCHEMA, "seed": self.seed,
                "prev_sha256": self.prev}
        event_hash = digest(canonical(body))
        record = {**body, "event_sha256": event_hash}
        self._file.write(canonical(record) + b"\n")
        self._file.flush()
        # A failed fsync must prevent the following label grant.
        os.fsync(self._file.fileno())
        self.prev = event_hash
        self.ack_count += 1
        return event_hash

    def prediction(self, clock: int) -> str:
        if type(clock) is not int or clock != self.next_clock or clock >= self.rows:
            raise ValueError("Noncontiguous prediction clock")
        event_id = self._append({
            "kind": "prediction_commit", "clock": clock,
            "origin_index": clock, "row_id": f"fixture:s{self.seed}:r{clock}",
            "maturity_index": clock + LATENCY,
            "fake_neural_token": fake_prediction(self.seed, clock),
        })
        self.prediction_ids[clock] = event_id
        self.durable_prediction_clock = clock
        self.next_clock += 1
        return event_id

    def release(self, clock: int, escrow: "FixtureEscrow") -> None:
        if type(clock) is not int or clock != self.next_clock - 1:
            raise ValueError("Label release must follow current clock prediction")
        if self.durable_prediction_clock != clock:
            raise ValueError("Current prediction lacks fsync acknowledgement")
        origin = clock - LATENCY
        if origin < 0:
            raise ValueError("Label has not matured")
        label = escrow._mature_label(self, clock, origin)
        self._append({
            "kind": "mature_label_grant", "clock": clock,
            "origin_index": origin, "row_id": f"fixture:s{self.seed}:r{origin}",
            "maturity_index": clock, "true_label": label,
            "origin_prediction_event_sha256": self.prediction_ids[origin],
            "current_prediction_event_sha256": self.prediction_ids[clock],
        })

    def seal(self) -> dict[str, Any]:
        if self._closed or self.next_clock != self.rows:
            raise ValueError("Cannot seal partial or previously sealed fixture")
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()
        self._closed = True
        payload = {
            "schema": SCHEMA, "seed": self.seed, "rows": self.rows,
            "event_count": self.ack_count,
            "final_event_sha256": self.prev,
            "journal_sha256": digest((self.directory / "events.jsonl").read_bytes()),
            "fixture_only": True,
            "real_runtime_attested": False,
            "external_append_order_witnessed": False,
            "label_process_isolated": False,
            "real_neural_trajectory_verified": False,
            "stage10a_release_ready": False,
            "stage10a_treatment_execution_authorized": False,
        }
        _new_json(self.directory / "seal.json", payload)
        return payload


class FixtureEscrow:
    """In-process illustrative label gate; NOT OS-enforced process isolation."""

    def __init__(self, seed: int):
        _valid(seed, LATENCY + 1)
        self.seed = seed
        self._released: set[int] = set()

    def _mature_label(self, witness: AppendWitness, clock: int, origin: int) -> int:
        if witness.seed != self.seed:
            raise ValueError("Cross-seed escrow access")
        if clock < origin + LATENCY or origin < 0:
            raise ValueError("Unavailable future label")
        if witness.prediction_ids.get(origin) is None:
            raise ValueError("Origin prediction absent")
        if witness.durable_prediction_clock != clock:
            raise ValueError("Current prediction is not durably acknowledged")
        if origin in self._released:
            raise ValueError("Duplicate label grant")
        self._released.add(origin)
        return fake_label(self.seed, origin)


def write_fixture(root: Path, seed: int, rows: int = LATENCY + 1) -> dict[str, Any]:
    _valid(seed, rows)
    witness = AppendWitness(Path(root) / f"seed-{seed}", seed, rows)
    escrow = FixtureEscrow(seed)
    for clock in range(rows):
        witness.prediction(clock)
        if clock >= LATENCY:
            witness.release(clock, escrow)
    return witness.seal()


