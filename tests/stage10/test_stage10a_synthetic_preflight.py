"""No raw CICIDS data, real predictions, checkpoints, or treatments."""
from __future__ import annotations

import hashlib
import json

import pytest

from tools.stage10.stage10a_synthetic_preflight import (
    FIXTURE_TAG, LATENCY, SyntheticPredictionJournal, run_synthetic_preflight,
)


def _token(i: int) -> str:
    return hashlib.sha256(f"synthetic-only-{i}".encode()).hexdigest()


def test_synthetic_receipt_and_no_pre_maturity_labels(tmp_path) -> None:
    target = tmp_path / "journal.jsonl"
    result = run_synthetic_preflight(target)
    assert result["row_count"] == 5002
    assert result["matured_label_count"] == 2
    assert result["treatment_execution_authorized"] is False
    assert result["neural_or_symbolic_treatment_executed"] is False
    events = [json.loads(line) for line in target.read_text().splitlines()]
    assert len(events) == 5004
    predictions = [e for e in events if e["event_type"] == "prediction"]
    labels = [e for e in events if e["event_type"] == "label_release"]
    assert len(predictions) == 5002
    assert [(e["origin_index"], e["logical_clock"]) for e in labels] == [
        (0, LATENCY), (1, LATENCY + 1),
    ]
    assert all("synthetic_binary_label" not in e and "label" not in e
               and "boundary_index" not in e for e in predictions)
    for item in labels:
        matching = next(i for i, e in enumerate(events) if e["event_type"] == "prediction"
                        and e["origin_index"] == item["origin_index"])
        assert matching < events.index(item)
        assert item["logical_clock"] >= item["maturity_index"]
    assert result["journal_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()


def test_only_fixture_token_and_binary_labels_allowed(tmp_path) -> None:
    with pytest.raises(ValueError, match="Synthetic-only"):
        SyntheticPredictionJournal(tmp_path / "bad", fixture_tag="original-csv",
                                  sealed_synthetic_labels=[0])
    with pytest.raises(ValueError, match="binary"):
        SyntheticPredictionJournal(tmp_path / "bad", fixture_tag=FIXTURE_TAG,
                                  sealed_synthetic_labels=[0, 2])


def test_out_of_order_and_duplicate_are_rejected_without_writing(tmp_path) -> None:
    path = tmp_path / "test.jsonl"
    with SyntheticPredictionJournal(path, fixture_tag=FIXTURE_TAG,
                                    sealed_synthetic_labels=[0, 1]) as journal:
        with pytest.raises(ValueError, match="exactly once"):
            journal.commit_prediction(1, _token(1))
        assert path.read_text() == ""
        assert journal.commit_prediction(0, _token(0)) == ()
        recorded = path.read_bytes()
        with pytest.raises(ValueError, match="exactly once"):
            journal.commit_prediction(0, _token(0))
        with pytest.raises(ValueError, match="SHA-256"):
            journal.commit_prediction(1, "prediction")
        assert path.read_bytes() == recorded


def test_write_once_nonoverwrite_and_partial_failure_preserved(tmp_path) -> None:
    path = tmp_path / "test.jsonl"
    with SyntheticPredictionJournal(path, fixture_tag=FIXTURE_TAG,
                                    sealed_synthetic_labels=[0]) as journal:
        journal.commit_prediction(0, _token(0))
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        SyntheticPredictionJournal(path, fixture_tag=FIXTURE_TAG,
                                   sealed_synthetic_labels=[0])
    assert path.read_bytes() == original


def test_count_is_bounded_synthetic_fixture_only(tmp_path) -> None:
    with pytest.raises(ValueError, match="straddle"):
        run_synthetic_preflight(tmp_path / "none", count=42)
    with pytest.raises(ValueError, match="straddle"):
        run_synthetic_preflight(tmp_path / "none", count=100000)
    assert not (tmp_path / "none").exists()


def test_three_arm_synthetic_digest_is_independently_verified(tmp_path) -> None:
    from tools.stage10.stage10a_synthetic_preflight import (
        verify_synthetic_three_arm_match,
    )
    paths = {arm: tmp_path / f"{arm}.jsonl" for arm in (
        "c_frozen_symbolic", "d_drift", "d_periodic"
    )}
    for path in paths.values():
        run_synthetic_preflight(path, count=LATENCY + 1)
    digest = verify_synthetic_three_arm_match(paths, count=LATENCY + 1)
    assert digest == hashlib.sha256(paths["c_frozen_symbolic"].read_bytes()).hexdigest()
    altered = paths["d_periodic"]
    content = altered.read_text()
    altered.write_text(content.replace('"synthetic_binary_label":0',
                                       '"synthetic_binary_label":1'))
    with pytest.raises(ValueError, match="tampering"):
        verify_synthetic_three_arm_match(paths, count=LATENCY + 1)


def test_synthetic_verifier_rejects_three_arm_missing_and_prediction_label_leak(tmp_path) -> None:
    from tools.stage10.stage10a_synthetic_preflight import (
        verify_synthetic_journal, verify_synthetic_three_arm_match,
    )
    path = tmp_path / "sealed.jsonl"
    run_synthetic_preflight(path, count=LATENCY + 1)
    with pytest.raises(ValueError, match="three frozen"):
        verify_synthetic_three_arm_match({"c_frozen_symbolic": path}, count=LATENCY + 1)
    first, rest = path.read_text().split("\n", 1)
    record = json.loads(first)
    record["true_label"] = 1
    path.write_text(json.dumps(record) + "\n" + rest)
    with pytest.raises(ValueError, match="tampering"):
        verify_synthetic_journal(path, count=LATENCY + 1)
