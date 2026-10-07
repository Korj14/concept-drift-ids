from __future__ import annotations

import inspect

import numpy as np

from concept_drift_ids.system_b_selection_robustness_evaluation import (
    _aggregate,
    _load_evaluation_partitions,
)


def test_robustness_evaluator_loads_only_pre_post() -> None:
    source = inspect.getsource(_load_evaluation_partitions)
    assert 'load_partition("pre_drift")' in source
    assert 'load_partition("post_drift")' in source
    assert "training" not in source
    assert "development" not in source


def test_aggregate_groups_variants_separately() -> None:
    rows = []
    for variant in ("v1", "v2"):
        for seed in range(5):
            rows.append({
                "variant_id": variant,
                "family": "x",
                "partition": "pre_drift",
                "seed": seed,
                "accuracy": 0.8 + 0.01 * seed,
                "balanced_accuracy": 0.8,
                "precision": 0.8,
                "recall": 0.8,
                "f1": 0.8,
                "fpr": 0.1,
                "mcc": 0.7,
                "roc_auc": 0.9,
                "average_precision": 0.9,
                "resolved_coverage": 0.9,
                "raw_activation_coverage": 0.9,
                "uncovered_rate": 0.1,
                "conflict_abstention_rate": 0.0,
                "symbolic_neural_fidelity": 0.95,
                "benign_resolved_coverage": 0.95,
                "attack_resolved_coverage": 0.7,
                "benign_symbolic_correctness": 1.0,
                "attack_symbolic_correctness": 0.8,
                "benign_symbolic_neural_fidelity": 1.0,
                "attack_symbolic_neural_fidelity": 0.9,
            })
    out = _aggregate(rows)
    accuracy = [row for row in out if row["metric"] == "accuracy"]
    assert len(accuracy) == 2
    assert {row["variant_id"] for row in accuracy} == {"v1", "v2"}
