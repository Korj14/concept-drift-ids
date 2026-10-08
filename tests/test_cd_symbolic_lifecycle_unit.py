from __future__ import annotations

import numpy as np
import pytest

from concept_drift_ids.cd_symbolic_lifecycle import (
    CandidateRule,
    OnlineRuleGate,
    active_rules_for_inference,
    apply_lifecycle_maintenance,
    evaluate_rule_mask,
    migrate_r0_v2_rules,
    verify_lifecycle_state,
    wilson_lower_bound,
)
from concept_drift_ids.symbolic import Condition, Rule


FEATURES = ("x", "y")


def _rule(
    *,
    rule_id: str = "r0",
    consequent: int = 1,
    confidence: float = 0.95,
) -> Rule:
    return Rule(
        rule_id=rule_id,
        lineage_id=rule_id,
        rule_base_version="R0.v2",
        seed=0,
        conditions=(Condition("x", ">", 0.5),),
        consequent=consequent,
        confidence=confidence,
        support=0.5,
        covered_count=50,
        class_precision=0.95,
        neural_fidelity=0.95,
        stability=1.0,
        complexity=1,
        lifecycle_state="active",
        source_candidate_id="source",
        validation_evidence_id="r0-validation",
    )


def _gate() -> OnlineRuleGate:
    return OnlineRuleGate(
        min_support=0.01,
        min_covered=4,
        min_class_precision=0.75,
        min_precision_lcb=0.60,
        min_neural_fidelity=0.75,
        min_fidelity_lcb=0.60,
        min_stability=0.60,
        max_complexity=4,
        bootstrap_replicates=10,
    )


def _validation(pass_rule: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.array(
        [
            [0.0, 0.0],
            [0.1, 0.0],
            [0.2, 0.0],
            [0.3, 0.0],
            [0.8, 0.0],
            [0.9, 0.0],
            [1.0, 0.0],
            [1.1, 0.0],
        ],
        dtype=np.float64,
    )
    if pass_rule:
        y = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int8)
        neural = y.copy()
    else:
        y = np.array([0, 0, 0, 0, 0, 0, 1, 1], dtype=np.int8)
        neural = y.copy()
    return x, y, neural


def test_wilson_fidelity_boundary_is_below_90_at_24_and_above_at_25() -> None:
    assert wilson_lower_bound(24, 24) < 0.90
    assert wilson_lower_bound(25, 25) >= 0.90


def test_online_gate_needs_25_for_primary_perfect_fidelity() -> None:
    gate = OnlineRuleGate(
        bootstrap_replicates=5,
        min_stability=0.0,
    )
    y24 = np.array([0] * 24 + [1], dtype=np.int8)
    neural24 = y24.copy()
    mask24 = np.array([True] * 24 + [False])
    e24 = evaluate_rule_mask(
        mask24,
        y_true=y24,
        neural_decision=neural24,
        consequent=0,
        complexity=1,
        gate=gate,
        bootstrap_random_state=1,
    )
    assert e24.covered_count == 24
    assert not e24.gate_pass
    assert e24.staleness_status == "evidence_insufficient"

    y25 = np.array([0] * 25 + [1], dtype=np.int8)
    neural25 = y25.copy()
    mask25 = np.array([True] * 25 + [False])
    e25 = evaluate_rule_mask(
        mask25,
        y_true=y25,
        neural_decision=neural25,
        consequent=0,
        complexity=1,
        gate=gate,
        bootstrap_random_state=1,
    )
    assert e25.covered_count == 25
    assert e25.class_precision_lcb >= 0.90
    assert e25.neural_fidelity_lcb >= 0.90


def test_r0_v2_migration_preserves_rule_semantics() -> None:
    source = _rule()
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[source],
        neural_checkpoint_sha256="checkpoint-a",
    )
    verify_lifecycle_state(state)
    active = active_rules_for_inference(state)
    assert len(active) == 1
    assert active[0].conditions == source.conditions
    assert active[0].consequent == source.consequent
    assert active[0].confidence == source.confidence
    assert state.rule_base_version_id == "d-s0-r0v2"
    assert state.version_number == 0


def test_active_fail_then_fail_demotes_then_retires() -> None:
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()],
        neural_checkpoint_sha256="checkpoint-a",
    )
    X, y, neural = _validation(False)

    first = apply_lifecycle_maintenance(
        state,
        candidates=[],
        X_validation=X,
        y_validation=y,
        neural_decision=neural,
        feature_names=FEATURES,
        opportunity_id=1,
        validation_evidence_id="v1",
        neural_checkpoint_sha256="checkpoint-b",
        publication_effective_index=20,
        bootstrap_random_state=4,
        gate=_gate(),
    )
    assert first.published
    assert first.state.active_revision_ids == ()
    latest = first.state.latest_by_semantic()
    only = next(iter(latest.values()))
    assert only.lifecycle_state == "demoted"
    assert only.failure_streak == 1

    second = apply_lifecycle_maintenance(
        first.state,
        candidates=[],
        X_validation=X,
        y_validation=y,
        neural_decision=neural,
        feature_names=FEATURES,
        opportunity_id=2,
        validation_evidence_id="v2",
        neural_checkpoint_sha256="checkpoint-b",
        publication_effective_index=40,
        bootstrap_random_state=5,
        gate=_gate(),
    )
    assert second.published is False
    assert second.state.rule_base_version_id == first.state.rule_base_version_id
    assert second.state.canonical_sha256 == first.state.canonical_sha256
    assert second.state.history_sha256 != first.state.history_sha256
    latest2 = second.state.latest_by_semantic()
    only2 = next(iter(latest2.values()))
    assert only2.lifecycle_state == "retired"
    assert only2.failure_streak == 2
    verify_lifecycle_state(second.state)


def test_demoted_rule_reactivates_on_later_full_gate_pass() -> None:
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()],
        neural_checkpoint_sha256="checkpoint-a",
    )
    Xf, yf, nf = _validation(False)
    failed = apply_lifecycle_maintenance(
        state,
        candidates=[],
        X_validation=Xf,
        y_validation=yf,
        neural_decision=nf,
        feature_names=FEATURES,
        opportunity_id=1,
        validation_evidence_id="v1",
        neural_checkpoint_sha256="checkpoint-b",
        publication_effective_index=20,
        bootstrap_random_state=7,
        gate=_gate(),
    )
    Xp, yp, npred = _validation(True)
    recovered = apply_lifecycle_maintenance(
        failed.state,
        candidates=[],
        X_validation=Xp,
        y_validation=yp,
        neural_decision=npred,
        feature_names=FEATURES,
        opportunity_id=2,
        validation_evidence_id="v2",
        neural_checkpoint_sha256="checkpoint-b",
        publication_effective_index=40,
        bootstrap_random_state=8,
        gate=_gate(),
    )
    assert recovered.published
    active = recovered.state.active_revisions()
    assert len(active) == 1
    assert active[0].lifecycle_state == "active"
    assert active[0].lifecycle_transition == "reactivated"
    assert active[0].failure_streak == 0


def test_exact_semantic_candidate_does_not_duplicate_active_rule() -> None:
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()],
        neural_checkpoint_sha256="checkpoint-a",
    )
    X, y, neural = _validation(True)
    candidate = CandidateRule(
        candidate_id="candidate-1",
        seed=0,
        conditions=(Condition("x", ">", 0.5),),
        consequent=1,
        generation_evidence_id="generation-1",
    )
    result = apply_lifecycle_maintenance(
        state,
        candidates=[candidate],
        X_validation=X,
        y_validation=y,
        neural_decision=neural,
        feature_names=FEATURES,
        opportunity_id=1,
        validation_evidence_id="validation-1",
        neural_checkpoint_sha256="checkpoint-b",
        publication_effective_index=20,
        bootstrap_random_state=9,
        gate=_gate(),
    )
    assert sum(
        decision["type"] == "existing_semantic_identity"
        for decision in result.decisions
    ) == 1
    semantic_ids = [
        revision.semantic_rule_id for revision in result.state.active_revisions()
    ]
    assert len(semantic_ids) == len(set(semantic_ids))


def test_validation_requires_both_classes() -> None:
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()],
        neural_checkpoint_sha256="checkpoint-a",
    )
    X = np.ones((8, 2), dtype=np.float64)
    y = np.ones(8, dtype=np.int8)
    result = apply_lifecycle_maintenance(
        state,
        candidates=[],
        X_validation=X,
        y_validation=y,
        neural_decision=y,
        feature_names=FEATURES,
        opportunity_id=1,
        validation_evidence_id="v1",
        neural_checkpoint_sha256="checkpoint-b",
        publication_effective_index=20,
        bootstrap_random_state=1,
        gate=_gate(),
    )
    assert not result.published
    assert result.maintenance_status == "insufficient_validation_class_diversity"
