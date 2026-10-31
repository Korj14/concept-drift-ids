"""Stage-10A synthetic-only single-writer/three-read-only-arm witness contract.

This is NOT a treatment runner, Phase-A execution, model identity verification,
or experimental outcome. It generates only deterministic synthetic tokens and
frozen-latency fixture labels, never imports datasets/models or fetches files.
An independent validator re-derives every expected event from the fixture
specification and hashes actual write-once bytes rather than trusting claims.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from tools.stage10.stage10a_isolation_contract import ARMS, LATENCY, SEEDS

FIXTURE = "stage10a-shared-writer-synthetic-only-v1"
MIN_COUNT = LATENCY + 1
MAX_COUNT = LATENCY + 3


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _write_new(path: Path, content: bytes) -> None:
    """Exclusive, durable output. Never overwrite or repair partial work."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _check_seed_count(seed: int, count: int) -> None:
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError("Only the five frozen synthetic seed IDs are supported")
    if type(count) is not int or not MIN_COUNT <= count <= MAX_COUNT:
        raise ValueError("Only bounded synthetic fixtures straddling 5000-row latency")


def _prediction(seed: int, i: int) -> dict[str, Any]:
    return {
        "event_type": "prediction", "logical_clock": i, "origin_index": i,
        "prediction_committed": True,
        "synthetic_neural_token_sha256": _sha(
            f"{FIXTURE}|seed={seed}|origin={i}|neural".encode("utf-8")),
    }


def _label_release(seed: int, current: int) -> dict[str, Any]:
    origin = current - LATENCY
    return {
        "event_type": "label_release", "logical_clock": current,
        "origin_index": origin, "maturity_index": origin + LATENCY,
        "synthetic_binary_label": (seed + origin) % 2,
    }


def _expected_events(seed: int, count: int) -> Iterator[dict[str, Any]]:
    for i in range(count):
        yield _prediction(seed, i)
        if i >= LATENCY:
            yield _label_release(seed, i)


def _seed_dir(root: Path, seed: int) -> Path:
    return root / f"seed-{seed}"


def write_shared_fixture(root: Path, *, seed: int, count: int = MIN_COUNT) -> None:
    """One shared writer per seed: persist prediction *before* label release.

    A durable event is fsynced before the label gate emits the matching mature
    label. Files are exclusive; any failed/partial attempt is left as evidence.
    No C, D-drift or D-periodic model or symbolic code is invoked.
    """
    _check_seed_count(seed, count)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    directory = _seed_dir(root, seed)
    directory.mkdir(mode=0o700, exist_ok=False)
    _write_new(directory / "attempt.json", _canonical({
        "fixture": FIXTURE, "seed": seed, "count": count,
        "writer_role": "single_shared_writer", "real_execution": False,
        "stage10a_treatment_execution_authorized": False,
    }))
    journal = directory / "shared.jsonl"
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        for event in _expected_events(seed, count):
            stream.write(_canonical(event))
            stream.flush()
            os.fsync(stream.fileno())
    raw = journal.read_bytes()
    _write_new(directory / "sealed.json", _canonical({
        "fixture": FIXTURE, "seed": seed, "count": count,
        "journal_sha256": _sha(raw), "journal_bytes": len(raw),
        "writer_role": "single_shared_writer", "real_execution": False,
        "stage10a_treatment_execution_authorized": False,
    }))


def _read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Malformed synthetic evidence JSON") from exc
    if type(data) is not dict or raw != _canonical(data):
        raise ValueError("Noncanonical synthetic evidence JSON")
    return data


def verify_shared_fixture(root: Path, *, seed: int, count: int = MIN_COUNT) -> tuple[str, str]:
    """Independently replay and hash actual immutable shared writer bytes."""
    _check_seed_count(seed, count)
    directory = _seed_dir(Path(root), seed)
    expected_attempt = {
        "fixture": FIXTURE, "seed": seed, "count": count,
        "writer_role": "single_shared_writer", "real_execution": False,
        "stage10a_treatment_execution_authorized": False,
    }
    if _read_json(directory / "attempt.json") != expected_attempt:
        raise ValueError("Shared writer attempt provenance mismatch")
    journal = (directory / "shared.jsonl").read_bytes()
    if not journal or not journal.endswith(b"\n"):
        raise ValueError("Synthetic journal incomplete")
    expected_iter = iter(_expected_events(seed, count))
    observed_count = 0
    for line in journal.splitlines(keepends=True):
        try:
            record = json.loads(line)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Malformed synthetic event") from exc
        expected = next(expected_iter, None)
        if expected is None or type(record) is not dict or line != _canonical(expected):
            raise ValueError("Synthetic writer order, maturity, or event payload changed")
        observed_count += 1
    if next(expected_iter, None) is not None or observed_count != 2 * count - LATENCY:
        raise ValueError("Synthetic writer omitted a required event")
    expected_seal = {
        "fixture": FIXTURE, "seed": seed, "count": count,
        "journal_sha256": _sha(journal), "journal_bytes": len(journal),
        "writer_role": "single_shared_writer", "real_execution": False,
        "stage10a_treatment_execution_authorized": False,
    }
    seal_path = directory / "sealed.json"
    if _read_json(seal_path) != expected_seal:
        raise ValueError("Shared writer seal does not match raw event bytes")
    return _sha(journal), _sha(seal_path.read_bytes())


def bind_readonly_arm(root: Path, *, seed: int, arm: str,
                      count: int = MIN_COUNT) -> None:
    """One canonical shared trace, arm-specific synthetic symbolic token ONLY."""
    if arm not in ARMS:
        raise ValueError("Unknown frozen arm")
    shared_sha, seal_sha = verify_shared_fixture(root, seed=seed, count=count)
    _write_new(_seed_dir(Path(root), seed) / f"arm-{arm}.json", _canonical({
        "fixture": FIXTURE, "seed": seed, "arm": arm,
        "shared_journal_sha256": shared_sha, "shared_seal_sha256": seal_sha,
        "shared_writer_role": "read_only", "neural_writer_invocations": 0,
        "symbolic_fixture_token_sha256": _sha(
            f"{FIXTURE}|seed={seed}|arm={arm}|symbolic".encode("utf-8")),
        "real_execution": False, "stage10a_treatment_execution_authorized": False,
    }))


def verify_bound_seed(root: Path, *, seed: int, count: int = MIN_COUNT) -> str:
    shared_sha, seal_sha = verify_shared_fixture(root, seed=seed, count=count)
    directory = _seed_dir(Path(root), seed)
    expected_files = {"attempt.json", "shared.jsonl", "sealed.json"} | {
        f"arm-{a}.json" for a in ARMS
    }
    if {p.name for p in directory.iterdir()} != expected_files:
        raise ValueError("Missing or unauthorized shared writer/arm evidence")
    for arm in ARMS:
        actual = _read_json(directory / f"arm-{arm}.json")
        expected = {
            "fixture": FIXTURE, "seed": seed, "arm": arm,
            "shared_journal_sha256": shared_sha, "shared_seal_sha256": seal_sha,
            "shared_writer_role": "read_only", "neural_writer_invocations": 0,
            "symbolic_fixture_token_sha256": _sha(
                f"{FIXTURE}|seed={seed}|arm={arm}|symbolic".encode("utf-8")),
            "real_execution": False, "stage10a_treatment_execution_authorized": False,
        }
        if actual != expected:
            raise ValueError("Arm diverged from one sealed shared neural/control writer")
    return shared_sha


def verify_bound_all_seeds(root: Path, *, count: int = MIN_COUNT) -> dict[str, Any]:
    """All five and only five independent synthetic seed writers; one/seed."""
    _check_seed_count(0, count)
    if {p.name for p in Path(root).iterdir()} != {f"seed-{s}" for s in SEEDS}:
        raise ValueError("Expected exactly five frozen seed writers")
    hashes = {str(seed): verify_bound_seed(root, seed=seed, count=count) for seed in SEEDS}
    if len(set(hashes.values())) != len(SEEDS):
        raise ValueError("Five seed fixtures are not independently identified")
    return {
        "fixture": FIXTURE, "scope": "synthetic_only_shared_writer_binding",
        "seed_shared_journal_sha256": hashes, "seeds": list(SEEDS),
        "arms_per_seed": list(ARMS), "label_latency_rows": LATENCY,
        "source_or_checkpoint_loaded": False,
        "model_loaded_or_predicted": False,
        "real_neural_control_trajectory_verified": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
    }
