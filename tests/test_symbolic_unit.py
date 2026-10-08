from __future__ import annotations

import numpy as np
import pytest

from concept_drift_ids.symbolic import (
    Condition,
    Rule,
    activation_mask,
    apply_redundancy_and_conflict_policy,
    bootstrap_gate_stability,
    canonicalize_conditions,
    fuse_scores,
    infer_symbolic,
    reporting_windows,
    rule_identifier,
    rule_quality,
    stratified_bootstrap_indices,
)


def _rule(rule_id: str, consequent: int, conditions: tuple[Condition, ...], *, confidence: float = 0.9) -> Rule:
    return Rule(
        rule_id=rule_id,
        lineage_id=rule_id,
        rule_base_version="R0.v1",
        seed=0,
        conditions=conditions,
        consequent=consequent,
        confidence=confidence,
        support=0.5,
        covered_count=10,
        class_precision=0.9,
        neural_fidelity=0.95,
        stability=1.0,
        complexity=len(conditions),
        lifecycle_state="active",
        source_candidate_id=f"candidate-{rule_id}",
        validation_evidence_id="dev-hash",
    )


def test_canonicalize_tightens_repeated_bounds_and_is_deterministic() -> None:
    conditions = canonicalize_conditions(
        [("b", "<=", 5.0), ("a", ">", 1.0), ("a", ">", 2.0), ("b", "<=", 4.0)],
        feature_order=("a", "b"),
    )
    assert conditions == (Condition("a", ">", 2.0), Condition("b", "<=", 4.0))
    assert rule_identifier(seed=0, conditions=conditions, consequent=1) == rule_identifier(
        seed=0, conditions=conditions, consequent=1
    )


def test_canonicalize_rejects_contradictory_interval() -> None:
    with pytest.raises(ValueError, match="Contradictory"):
        canonicalize_conditions([("a", ">", 2.0), ("a", "<=", 2.0)], feature_order=("a",))


def test_activation_boundaries_are_exact() -> None:
    X = np.array([[1.0], [2.0], [3.0]])
    np.testing.assert_array_equal(
        activation_mask(X, feature_names=("x",), conditions=(Condition("x", ">", 2.0),)),
        [False, False, True],
    )
    np.testing.assert_array_equal(
        activation_mask(X, feature_names=("x",), conditions=(Condition("x", "<=", 2.0),)),
        [True, True, False],
    )


def test_rule_quality_separates_class_precision_and_neural_fidelity() -> None:
    quality = rule_quality(
        np.array([True, True, False, False]),
        y_true=np.array([1, 0, 1, 0]),
        neural_decision=np.array([1, 1, 0, 0]),
        consequent=1,
    )
    assert quality["support"] == 0.5
    assert quality["class_precision"] == 0.5
    assert quality["neural_fidelity"] == 1.0


def test_bootstrap_stability_is_deterministic() -> None:
    y = np.array([0] * 50 + [1] * 50, dtype=np.int8)
    indices_a = stratified_bootstrap_indices(y, replicates=20, random_state=11)
    indices_b = stratified_bootstrap_indices(y, replicates=20, random_state=11)
    for left, right in zip(indices_a, indices_b):
        np.testing.assert_array_equal(left, right)
    stability = bootstrap_gate_stability(
        np.ones(100, dtype=bool),
        y_true=y,
        neural_decision=y,
        consequent=1,
        bootstrap_indices=indices_a,
        min_support=0.1,
        min_covered=10,
        min_precision=0.4,
        min_fidelity=0.4,
    )
    assert 0 <= stability <= 1


def test_conflict_abstains_and_fusion_falls_back_to_neural() -> None:
    X = np.array([[0.0], [2.0], [4.0]])
    rules = [
        _rule("benign", 0, (Condition("x", ">", 1.0),)),
        _rule("attack", 1, (Condition("x", "<=", 3.0),)),
    ]
    symbolic = infer_symbolic(X, feature_names=("x",), rules=rules)
    np.testing.assert_array_equal(symbolic["covered"], [True, False, True])
    np.testing.assert_array_equal(symbolic["conflict_abstain"], [False, True, False])
    neural = np.array([0.2, 0.7, 0.8])
    fused = fuse_scores(neural, symbolic, neural_weight=0.5)
    assert fused[1] == pytest.approx(neural[1])


def test_uncovered_has_no_symbolic_effect() -> None:
    X = np.array([[0.0], [1.0]])
    symbolic = infer_symbolic(
        X,
        feature_names=("x",),
        rules=[_rule("r", 1, (Condition("x", ">", 5.0),))],
    )
    neural = np.array([0.1, 0.9])
    np.testing.assert_allclose(fuse_scores(neural, symbolic, neural_weight=0.5), neural)


def test_same_class_redundancy_keeps_stronger_rule() -> None:
    left = _rule("left", 1, (Condition("x", ">", 0.0),), confidence=0.95)
    right = _rule("right", 1, (Condition("x", ">", 0.0),), confidence=0.85)
    masks = {
        "left": np.array([False, True, True]),
        "right": np.array([False, True, True]),
    }
    active, decisions = apply_redundancy_and_conflict_policy(
        [left, right], masks, same_class_overlap=0.95, cross_class_overlap=0.50
    )
    assert [rule.rule_id for rule in active] == ["left"]
    assert decisions[0]["type"] == "same_class_redundancy"


def test_reporting_windows_merge_tiny_tail_without_dropping_rows() -> None:
    assert reporting_windows(11_200) == ((0, 5000), (5000, 10000), (10000, 11200))
    assert reporting_windows(10_500) == ((0, 5000), (5000, 10500))
    windows = reporting_windows(69_260)
    assert windows[0] == (0, 5000)
    assert windows[-1][1] == 69_260
    assert sum(stop - start for start, stop in windows) == 69_260
