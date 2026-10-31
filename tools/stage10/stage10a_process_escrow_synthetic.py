"""Synthetic Stage-10A process-separated append/label-maturity handshake.

NON-PRODUCTION. This is a cross-process *contract test*, not an enforced
confidential-label boundary, attested runtime, durable independent fsync proof,
real neural trajectory, scientific experiment, or Stage-10A RELEASE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

SCHEMA = "stage10a-process-escrow-synthetic-v1"
LATENCY = 5_000
SEEDS = tuple(range(5))
ROWS = (LATENCY + 1, LATENCY + 2)
ZERO = "0" * 64
ROOT = Path(__file__).resolve().parents[2]


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def token(seed: int, clock: int) -> str:
    return sha(f"{SCHEMA}|neural-fixture-token|{seed}|{clock}".encode())


def _validate(seed: int, rows: int) -> None:
    if type(seed) is not int or seed not in SEEDS or type(rows) is not int or rows not in ROWS:
        raise ValueError("Only bounded 5,001/5,002-row synthetic seed 0..4 fixtures")


def _write_new(path: Path, value: dict[str, Any]) -> None:
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def _record(seed: int, clock: int, previous: str) -> dict[str, Any]:
    core = {"schema": SCHEMA, "seed": seed, "kind": "prediction_commit",
            "clock": clock, "origin_index": clock,
            "row_id": f"synthetic:seed-{seed}:row-{clock}",
            "maturity_index": clock + LATENCY,
            "fake_prediction_sha256": token(seed, clock),
            "previous_prediction_sha256": previous}
    return {**core, "record_sha256": sha(canonical(core))}


def _synthetic_label(seed: int, origin: int) -> int:
    # This deterministic fixture label is not confidential even across PIDs.
    return (seed + 7 * origin) % 2


def run_escrow_worker(directory: Path, seed: int, rows: int) -> int:
    """Separate OS process, never a neural/model process. Its receipt is not a trusted signature."""
    _validate(seed, rows)
    journal_path = directory / "predictions.jsonl"
    receipts_path = directory / "escrow_receipts.jsonl"
    previous = ZERO
    expected_clock = 0
    with journal_path.open("rb", buffering=0) as predictions, receipts_path.open("xb") as receipts:
        for raw_request in sys.stdin.buffer:
            try:
                request = json.loads(raw_request)
                if type(request) is not dict or set(request) not in ({"op", "seed", "clock"}, {"op"}):
                    raise ValueError("Unexpected escrow request fields")
                if request["op"] == "close":
                    if set(request) != {"op"} or expected_clock != rows:
                        raise ValueError("Premature escrow close")
                    if predictions.read(1):
                        raise ValueError("Unacknowledged prediction bytes at close")
                    result = {"ok": True, "status": "closed", "escrow_pid": os.getpid()}
                    sys.stdout.buffer.write(canonical(result) + b"\n")
                    sys.stdout.buffer.flush()
                    return 0
                if (request["op"] != "observe" or type(request["seed"]) is not int or
                    request["seed"] != seed or type(request["clock"]) is not int or
                    request["clock"] != expected_clock or expected_clock >= rows):
                    raise ValueError("Wrong seed, repeated, premature or missing clock")
                line = predictions.readline()
                if not line.endswith(b"\n"):
                    raise ValueError("Prediction not present as complete persisted record")
                observed = json.loads(line)
                expected = _record(seed, expected_clock, previous)
                if observed != expected or line != canonical(expected) + b"\n":
                    raise ValueError("Prediction bytes do not match frozen synthetic contract")
                previous = expected["record_sha256"]
                origin = expected_clock - LATENCY
                receipt = {"schema": SCHEMA, "seed": seed, "clock": expected_clock,
                           "prediction_sha256": previous, "escrow_pid": os.getpid(),
                           "mature_label_origin": origin if origin >= 0 else None,
                           "mature_label": _synthetic_label(seed, origin) if origin >= 0 else None}
                receipts.write(canonical(receipt) + b"\n")
                receipts.flush()
                os.fsync(receipts.fileno())
                result = {"ok": True, "clock": expected_clock, "escrow_pid": os.getpid(),
                          "mature_label_origin": receipt["mature_label_origin"],
                          "mature_label": receipt["mature_label"]}
                sys.stdout.buffer.write(canonical(result) + b"\n")
                sys.stdout.buffer.flush()
                expected_clock += 1
            except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
                sys.stdout.buffer.write(canonical({"ok": False, "error": type(exc).__name__}) + b"\n")
                sys.stdout.buffer.flush()
                return 2
    return 3


def generate_fixture(root: Path, seed: int, rows: int = LATENCY + 1) -> dict[str, Any]:
    """Only writes fake predictions. It does not read original data or acquire future labels."""
    _validate(seed, rows)
    directory = Path(root) / f"seed-{seed}"
    directory.mkdir(parents=True, exist_ok=False)
    _write_new(directory / "attempt.json", {
        "schema": SCHEMA, "seed": seed, "rows": rows, "writer_pid": os.getpid(),
        "fixture_only": True, "model_loaded": False,
        "stage10a_treatment_execution_authorized": False})
    cmd = [sys.executable, "-m", "tools.stage10.stage10a_process_escrow_synthetic",
           "--escrow-worker", "--directory", str(directory.resolve()),
           "--seed", str(seed), "--rows", str(rows)]
    # Create the append-only journal before starting the separate escrow reader.
    journal = (directory / "predictions.jsonl").open("xb")
    worker = subprocess.Popen(cmd, cwd=str(ROOT), stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    previous = ZERO
    last_pid: int | None = None
    try:
        assert worker.stdin is not None and worker.stdout is not None
        with journal as predictions:
            for clock in range(rows):
                record = _record(seed, clock, previous)
                predictions.write(canonical(record) + b"\n")
                predictions.flush()
                os.fsync(predictions.fileno())
                worker.stdin.write(canonical({"op": "observe", "seed": seed, "clock": clock}) + b"\n")
                worker.stdin.flush()
                response = json.loads(worker.stdout.readline())
                if response.get("ok") is not True or response.get("clock") != clock:
                    raise RuntimeError("Escrow worker failed to validate current prediction")
                last_pid = response["escrow_pid"]
                if last_pid == os.getpid():
                    raise RuntimeError("Escrow not in separate process")
                origin = clock - LATENCY
                if (response.get("mature_label_origin") != (origin if origin >= 0 else None) or
                    (response.get("mature_label") is not None if origin < 0 else
                     type(response.get("mature_label")) is not int or response["mature_label"] not in (0, 1))):
                    raise RuntimeError("Escrow response violates delayed-label maturity")
                previous = record["record_sha256"]
        worker.stdin.write(canonical({"op": "close"}) + b"\n")
        worker.stdin.flush()
        close = json.loads(worker.stdout.readline())
        if close != {"ok": True, "status": "closed", "escrow_pid": last_pid}:
            raise RuntimeError("Escrow close failed")
        worker.stdin.close()
        if worker.wait(timeout=15) != 0:
            raise RuntimeError("Escrow worker exited unsuccessfully")
        receipt_bytes = (directory / "escrow_receipts.jsonl").read_bytes()
        prediction_bytes = (directory / "predictions.jsonl").read_bytes()
        seal = {"schema": SCHEMA, "seed": seed, "rows": rows,
                "prediction_sha256": sha(prediction_bytes),
                "escrow_receipts_sha256": sha(receipt_bytes),
                "last_prediction_sha256": previous,
                "writer_pid": os.getpid(), "escrow_pid": last_pid,
                "fixture_only": True, "same_user_processes_not_an_access_boundary": True,
                "external_runtime_attested": False, "real_durable_fsync_attested": False,
                "real_process_access_controls_verified": False,
                "real_neural_state_verified": False, "release_signed": False,
                "stage10a_treatment_execution_authorized": False}
        _write_new(directory / "seal.json", seal)
        return seal
    except Exception as exc:
        _write_new(directory / "failure.json", {"schema": SCHEMA, "seed": seed,
                    "type": type(exc).__name__, "fixture_only": True,
                    "release_signed": False})
        raise
    finally:
        if worker.poll() is None:
            worker.kill()
        worker.wait(timeout=15)
        if worker.stdin and not worker.stdin.closed:
            worker.stdin.close()
        if worker.stdout:
            worker.stdout.close()
        if worker.stderr:
            worker.stderr.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--escrow-worker", action="store_true")
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--rows", type=int)
    args = parser.parse_args()
    if not args.escrow_worker or args.directory is None:
        raise SystemExit("No production CLI or treatment entrypoint exists")
    raise SystemExit(run_escrow_worker(args.directory, args.seed, args.rows))


if __name__ == "__main__":
    main()
