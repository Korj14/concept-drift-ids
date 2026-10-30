"""Stage-10A source-independent synthetic fixture: commit-before-label proof.

NEVER accepts raw datasets, neural checkpoints, predictions or treatment arms.
No treatment runner or Stage-10 RELEASE is implemented. The journal is a
write-once test of durable prediction commitment preceding label maturity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Sequence

FIXTURE_TAG = "stage10a-synthetic-fixture-only-v1"
LATENCY = 5000
TOKEN_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class SyntheticPredictionJournal:
    """Persist synthetic prediction tokens before acknowledging delayed labels.

    The sealed labels are intentionally supplied only to a fixture-specific
    private gate. This does not verify real model/data provenance.
    """

    def __init__(
        self,
        output_path: Path,
        *,
        fixture_tag: str,
        sealed_synthetic_labels: Sequence[int],
    ) -> None:
        if fixture_tag != FIXTURE_TAG:
            raise ValueError("Synthetic-only fixture identity is required.")
        if not sealed_synthetic_labels or any(
            type(label) is not int or label not in (0, 1)
            for label in sealed_synthetic_labels
        ):
            raise ValueError("Fixture labels must be a nonempty binary sequence.")
        self._labels = tuple(sealed_synthetic_labels)
        self._next_index = 0
        self._failed = False
        self._closed = False
        self._releases = 0
        self._path = Path(output_path)
        # Intentionally do NOT mkdir/modify the repository or allow overwrite.
        self._file = self._path.open("x", encoding="utf-8", newline="\n")

    def _persist(self, event: dict[str, Any]) -> None:
        try:
            self._file.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            self._file.flush()
            os.fsync(self._file.fileno())
        except BaseException:
            self._failed = True
            raise

    def commit_prediction(
        self, logical_index: int, synthetic_prediction_token_sha256: str
    ) -> tuple[dict[str, Any], ...]:
        if self._closed or self._failed:
            raise RuntimeError("Journal is closed or failed; never resume partial output.")
        if (type(logical_index) is not int or logical_index != self._next_index
            or logical_index >= len(self._labels)):
            raise ValueError("Predictions must be committed exactly once in order.")
        if not isinstance(synthetic_prediction_token_sha256, str) or not (
            TOKEN_PATTERN.fullmatch(synthetic_prediction_token_sha256)
        ):
            raise ValueError("Synthetic token must be a SHA-256 digest.")
        # Write and fsync a synthetic prediction event FIRST. No ground truth.
        self._persist({
            "event_type": "prediction", "logical_clock": logical_index,
            "origin_index": logical_index, "prediction_committed": True,
            "synthetic_token_sha256": synthetic_prediction_token_sha256,
        })
        self._next_index += 1
        eligible_origin = logical_index - LATENCY
        if eligible_origin < 0:
            return ()
        released = {
            "event_type": "label_release", "logical_clock": logical_index,
            "origin_index": eligible_origin,
            "maturity_index": eligible_origin + LATENCY,
            "synthetic_binary_label": self._labels[eligible_origin],
        }
        self._persist(released)
        self._releases += 1
        return (released,)

    def close(self) -> dict[str, Any]:
        if not self._closed:
            self._file.close()
            self._closed = True
        if self._failed:
            raise RuntimeError("Partial synthetic journal is failed; retain for audit.")
        return {
            "scope": FIXTURE_TAG,
            "row_count": self._next_index,
            "matured_label_count": self._releases,
            "label_latency_rows": LATENCY,
            "journal_sha256": hashlib.sha256(self._path.read_bytes()).hexdigest(),
            "treatment_execution_authorized": False,
            "neural_or_symbolic_treatment_executed": False,
        }

    def __enter__(self) -> SyntheticPredictionJournal:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if not self._closed:
            self._file.close()
            self._closed = True
        if exc_type is not None:
            self._failed = True


def run_synthetic_preflight(output: Path, *, count: int = LATENCY + 2) -> dict[str, Any]:
    """Small synthetic-only smoke; intentionally does not read a source CSV."""
    if count < LATENCY + 1 or count > LATENCY + 10:
        raise ValueError("Synthetic fixture count must straddle the fixed latency.")
    labels = [i % 2 for i in range(count)]
    with SyntheticPredictionJournal(
        output, fixture_tag=FIXTURE_TAG, sealed_synthetic_labels=labels
    ) as journal:
        for i in range(count):
            token = hashlib.sha256(f"synthetic-fixture-token-{i}".encode()).hexdigest()
            journal.commit_prediction(i, token)
        report = journal.close()
    if report["matured_label_count"] != count - LATENCY:
        raise AssertionError("Synthetic latency invariant failed.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="SYNTHETIC ONLY; NO Stage-10A treatments")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixture-tag", required=True)
    args = parser.parse_args()
    if args.fixture_tag != FIXTURE_TAG:
        parser.error("Only a synthetic fixture tag is supported")
    print(json.dumps(run_synthetic_preflight(args.output), sort_keys=True))


if __name__ == "__main__":
    main()


def verify_synthetic_journal(path: Path, *, count: int) -> str:
    """Re-derive a fixture digest from a durable event log, not reported claims."""
    if count < LATENCY + 1 or count > LATENCY + 10:
        raise ValueError("Synthetic verification count must straddle latency.")
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Synthetic journal JSONL is malformed.") from exc
    expected: list[dict[str, Any]] = []
    for i in range(count):
        expected.append({
            "event_type": "prediction", "logical_clock": i,
            "origin_index": i, "prediction_committed": True,
            "synthetic_token_sha256": hashlib.sha256(
                f"synthetic-fixture-token-{i}".encode()
            ).hexdigest(),
        })
        if i >= LATENCY:
            expected.append({
                "event_type": "label_release", "logical_clock": i,
                "origin_index": i - LATENCY, "maturity_index": i,
                "synthetic_binary_label": (i - LATENCY) % 2,
            })
    if records != expected:
        raise ValueError("Synthetic trace is not canonical; leakage/tampering/order violation.")
    return digest


def verify_synthetic_three_arm_match(paths: dict[str, Path], *, count: int) -> str:
    """Fixture-only evidence parity; NOT a neural C/D trajectory verifier."""
    if set(paths) != {"c_frozen_symbolic", "d_drift", "d_periodic"}:
        raise ValueError("Exactly three frozen synthetic arm identifiers required.")
    digests = {arm: verify_synthetic_journal(path, count=count)
               for arm, path in paths.items()}
    if len(set(digests.values())) != 1:
        raise ValueError("Synthetic shared-journal mismatch across three arms.")
    return digests["c_frozen_symbolic"]
