from __future__ import annotations

import inspect

import numpy as np

import concept_drift_ids.system_b_v2_evaluation as evaluation
from concept_drift_ids.system_b_r0_v2 import ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256


def _symbolic(covered, symbolic_class, neural=None):
    covered = np.asarray(covered, dtype=bool)
    n = len(covered)
    return {
        "covered": covered,
        "uncovered": ~covered,
        "raw_activated": covered.copy(),
        "conflict_abstain": np.zeros(n, dtype=bool),
        "symbolic_class": np.asarray(symbolic_class, dtype=np.int8),
    }


def test_v2_evaluator_has_separate_immutable_directory() -> None:
    assert evaluation.EVALUATION_ID == "system_b_v2_corrected_evaluation_v1"
    assert evaluation.EVALUATION_DIR.name == "system_b_v2_corrected_v1"
    assert ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256 == (
        "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483"
    )


def test_v2_evaluator_partition_gate_only_allows_pre_post(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        evaluation,
        "load_partition",
        lambda name: calls.append(name) or name,
    )
    assert evaluation._load_evaluation_partition("pre_drift") == "pre_drift"
    assert evaluation._load_evaluation_partition("post_drift") == "post_drift"
    assert calls == ["pre_drift", "post_drift"]


def test_v2_evaluator_does_not_read_v1_evaluation() -> None:
    source = inspect.getsource(evaluation.evaluate_r0_v2)
    assert "system_b_v1" not in source
    assert "supplement" not in source
    assert "training" not in source.split("for partition_name", 1)[1].split(
        "metric_rows", 1
    )[0]
    assert "development" not in source.split("for partition_name", 1)[1].split(
        "metric_rows", 1
    )[0]


def test_class_conditional_symbolic_summary_separates_attack_correctness() -> None:
    symbolic = _symbolic(
        [True, True, True, True],
        [0, 0, 0, 1],
    )
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    neural = np.array([0, 0, 1, 1], dtype=np.int8)
    out = evaluation._class_conditional_symbolic_summary(symbolic, neural, y)
    assert out["benign_resolved_coverage"] == 1.0
    assert out["attack_resolved_coverage"] == 1.0
    assert out["benign_symbolic_correctness"] == 1.0
    assert out["attack_symbolic_correctness"] == 0.5
    assert out["attack_symbolic_neural_fidelity"] == 0.5


def test_timing_protocol_is_frozen() -> None:
    assert evaluation.TIMING_WARMUP_REPEATS == 1
    assert evaluation.TIMING_MEASURED_REPEATS == 5
