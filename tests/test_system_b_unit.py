from __future__ import annotations

import json

import numpy as np
import pytest

import concept_drift_ids.system_b as system_b


def _uncovered(n: int) -> dict[str, np.ndarray]:
    return {
        "p_rule_attack": np.full(n, np.nan),
        "covered": np.zeros(n, dtype=bool),
        "uncovered": np.ones(n, dtype=bool),
        "conflict_abstain": np.zeros(n, dtype=bool),
        "raw_activated": np.zeros(n, dtype=bool),
        "symbolic_class": np.full(n, -1, dtype=np.int8),
        "activation_matrix": np.zeros((n, 0), dtype=bool),
    }


def test_build_partition_loader_can_only_request_training_and_development(monkeypatch) -> None:
    calls: list[str] = []
    def fake_load(name: str):
        calls.append(name)
        return name
    monkeypatch.setattr(system_b, "load_partition", fake_load)
    assert system_b._load_build_partitions() == ("training", "development")
    assert calls == ["training", "development"]
    assert "pre_drift" not in calls and "post_drift" not in calls


def test_global_lambda_tie_prefers_more_neural_weight() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    neural = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)
    inputs = {
        seed: (y, neural, _uncovered(len(y)))
        for seed in system_b.SYSTEM_B_CONFIG["seeds"]
    }
    selected, results, rows = system_b._select_global_fusion(inputs)
    assert selected == 1.0
    assert len(results) == 5
    assert len(rows) == 30


def test_system_b_v1_forbids_calibration_and_freezes_cpu_backend() -> None:
    assert system_b.SYSTEM_B_CONFIG["fusion"]["probability_calibration"] == "none"
    assert system_b.SYSTEM_B_CONFIG["backend"] == "cpu"


def test_environment_rejects_non_cpu_before_data_access() -> None:
    with pytest.raises(ValueError, match="CPU"):
        system_b._require_environment("cuda")


def test_json_writer_refuses_overwrite(tmp_path) -> None:
    path = tmp_path / "frozen.json"
    system_b._write_json_new(path, {"a": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}
    with pytest.raises(FileExistsError, match="overwrite"):
        system_b._write_json_new(path, {"a": 2})


def test_development_split_is_deterministic_and_disjoint() -> None:
    y = np.array([0] * 90 + [1] * 10, dtype=np.int8)
    va, fu = system_b._development_split(y)
    va2, fu2 = system_b._development_split(y)
    np.testing.assert_array_equal(va, va2)
    np.testing.assert_array_equal(fu, fu2)
    assert not set(va).intersection(fu)
    assert len(va) + len(fu) == len(y)


def test_root_runner_declares_system_b_command() -> None:
    text = (system_b.PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
    assert '"system-b"' in text
    assert "from concept_drift_ids.system_b import main as run_system_b" in text


def test_single_class_window_keeps_threshold_metrics_and_marks_ranking_undefined() -> None:
    metrics = system_b._safe_window_metrics(
        np.array([0, 0, 0], dtype=np.int8),
        np.array([0.1, 0.2, 0.3], dtype=np.float64),
        0.5,
    )
    assert metrics["accuracy"] == 1.0
    assert metrics["balanced_accuracy"] == 1.0
    assert metrics["fpr"] == 0.0
    assert metrics["roc_auc"] is None
    assert metrics["average_precision"] is None



def test_symbolic_summary_marks_fidelity_undefined_without_resolved_coverage() -> None:
    summary = system_b._symbolic_summary(
        _uncovered(3),
        np.array([0, 1, 0], dtype=np.int8),
    )
    assert summary["resolved_coverage"] == 0.0
    assert summary["uncovered_rate"] == 1.0
    assert summary["symbolic_neural_fidelity"] is None


def test_metric_tables_preserve_paired_seed_effects() -> None:
    rows = []
    for partition, offset in (("pre_drift", 0.0), ("post_drift", 0.1)):
        for seed in system_b.SYSTEM_B_CONFIG["seeds"]:
            row = {
                "system_id": system_b.SYSTEM_B_ID,
                "scenario_id": "scenario",
                "partition": partition,
                "seed": seed,
                "threshold": 0.5,
            }
            for metric in system_b.EVIDENCE_METRICS:
                row[metric] = 0.5 + offset
            rows.append(row)

    metric_rows, aggregate_rows, paired_rows, aggregate_paired = (
        system_b._build_metric_tables(rows, scenario_version=1)
    )

    assert len(metric_rows) == 2 * 5 * len(system_b.EVIDENCE_METRICS)
    assert len(aggregate_rows) == 2 * len(system_b.EVIDENCE_METRICS)
    assert len(paired_rows) == 5 * len(system_b.EVIDENCE_METRICS)
    assert len(aggregate_paired) == len(system_b.EVIDENCE_METRICS)
    assert all(row["delta"] == pytest.approx(0.1) for row in paired_rows)


def test_rule_staleness_delta_uses_frozen_gate_without_composite_index() -> None:
    base = {
        "system_id": system_b.SYSTEM_B_ID,
        "scenario_id": "scenario",
        "seed": 0,
        "rule_id": "r0",
        "consequent": 1,
        "complexity": 2,
        "support": 0.02,
        "covered_count": 200,
        "class_precision": 0.95,
        "neural_fidelity": 0.95,
        "stability": 1.0,
        "activation_rate": 0.02,
    }
    pre = dict(base, partition="pre_drift")
    post = dict(
        base,
        partition="post_drift",
        class_precision=0.70,
        activation_rate=0.01,
    )
    rows = system_b._rule_staleness_deltas(
        [pre, post],
        scenario_version=1,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["pre_gate_pass"] is True
    assert row["post_gate_pass"] is False
    assert row["gate_transition"] == "pass_to_fail"
    assert row["delta_class_precision"] == pytest.approx(-0.25)
    assert "staleness_index" not in row


def test_evaluator_pins_the_accepted_r0_manifest_identity() -> None:
    assert system_b.ACCEPTED_SYSTEM_B_MANIFEST_SHA256 == (
        "6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8"
    )
