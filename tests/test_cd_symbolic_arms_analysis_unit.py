from __future__ import annotations

import numpy as np
import pytest

from concept_drift_ids.cd_analysis import (
    build_confirmatory_family,
    exact_one_sided_sign_pvalue,
    holm_bonferroni,
    paired_effect_summary,
    recovery_time,
)
from concept_drift_ids.cd_symbolic_arms import (
    PRIMARY_PERIODIC_CLOCKS,
    SymbolicOperatorConfig,
    SymbolicOpportunity,
    SymbolicValidationRecord,
    collect_independent_validation_block,
    drift_symbolic_opportunities,
    frozen_periodic_opportunities,
    open_symbolic_transaction,
    verify_periodic_schedule,
    verify_primary_symbolic_operator_config,
    verify_trigger_operator_identity,
)
from concept_drift_ids.cd_symbolic_evaluation import (
    evaluate_symbolic_arm,
    macro_correct_symbolic_coverage,
    verify_lambda_one_negative_control,
)
from concept_drift_ids.cd_symbolic_lifecycle import migrate_r0_v2_rules
from concept_drift_ids.symbolic import Condition, Rule


FEATURES = ("x",)


def _rule(
    *,
    rule_id: str,
    condition: Condition,
    consequent: int,
    confidence: float = 1.0,
) -> Rule:
    return Rule(
        rule_id=rule_id,
        lineage_id=rule_id,
        rule_base_version="R0.v2",
        seed=0,
        conditions=(condition,),
        consequent=consequent,
        confidence=confidence,
        support=0.5,
        covered_count=50,
        class_precision=1.0,
        neural_fidelity=1.0,
        stability=1.0,
        complexity=1,
        lifecycle_state="active",
        source_candidate_id="source",
        validation_evidence_id="r0-validation",
    )


def test_periodic_schedule_is_exact_and_boundary_independent() -> None:
    opportunities = frozen_periodic_opportunities()
    verify_periodic_schedule(opportunities)
    assert tuple(item.logical_clock for item in opportunities) == (
        PRIMARY_PERIODIC_CLOCKS
    )
    assert 69_260 not in PRIMARY_PERIODIC_CLOCKS


def test_drift_symbolic_budget_uses_only_first_four_confirmed_events() -> None:
    events = [
        {
            "event_type": "drift_event",
            "status": "confirmed",
            "event_id": f"drift-{i}",
            "logical_clock": 100 * i,
            "neural_checkpoint_sha256": f"c{i}",
        }
        for i in range(1, 7)
    ]
    opportunities = drift_symbolic_opportunities(events)
    assert len(opportunities) == 4
    assert [item.opportunity_id for item in opportunities] == [1, 2, 3, 4]
    assert [item.logical_clock for item in opportunities] == [100, 200, 300, 400]


def test_trigger_operator_identity_fails_on_divergence() -> None:
    verify_trigger_operator_identity("same", "same")
    with pytest.raises(ValueError, match="diverge"):
        verify_trigger_operator_identity("drift", "periodic")


def test_validation_block_is_future_disjoint_and_checkpoint_pure() -> None:
    opportunity = SymbolicOpportunity(
        arm="d_drift",
        opportunity_id=1,
        source="drift",
        logical_clock=10,
        shared_neural_checkpoint_sha256="child",
    )
    operator = SymbolicOperatorConfig(validation_rows=4)
    transaction = open_symbolic_transaction(
        opportunity,
        neural_checkpoint_sha256="child",
        checkpoint_publication_effective_index=20,
        generation_row_ids=[f"g-{i}" for i in range(10_000)],
        generation_evidence_id="generation",
        candidates=[],
        operator_config=operator,
    )
    records = [
        SymbolicValidationRecord(
            row_id=f"v-{i}",
            origin_index=20 + i,
            maturity_index=25 + i,
            neural_checkpoint_sha256="child",
            features=np.array([float(i)]),
            true_label=i % 2,
            neural_decision=i % 2,
        )
        for i in range(6)
    ]
    result = collect_independent_validation_block(
        records,
        transaction,
        superseding_checkpoint_effective_index=None,
        required_rows=4,
    )
    assert result.status == "complete"
    assert result.row_ids == ("v-0", "v-1", "v-2", "v-3")
    assert not set(result.row_ids).intersection(transaction.generation_row_ids)


def test_validation_supersession_censors_old_checkpoint_evidence() -> None:
    opportunity = SymbolicOpportunity(
        arm="d_periodic",
        opportunity_id=1,
        source="periodic",
        logical_clock=10,
        shared_neural_checkpoint_sha256=None,
    )
    transaction = open_symbolic_transaction(
        opportunity,
        neural_checkpoint_sha256="child",
        checkpoint_publication_effective_index=20,
        generation_row_ids=[f"g-{i}" for i in range(10_000)],
        generation_evidence_id="generation",
        candidates=[],
    )
    records = [
        SymbolicValidationRecord(
            row_id=f"v-{i}",
            origin_index=20 + i,
            maturity_index=25 + i,
            neural_checkpoint_sha256="child",
            features=np.array([0.0]),
            true_label=i % 2,
            neural_decision=i % 2,
        )
        for i in range(20)
    ]
    result = collect_independent_validation_block(
        records,
        transaction,
        superseding_checkpoint_effective_index=30,
    )
    assert result.status == "superseded_before_validation"
    assert len(result.records) < 10_000


def test_mcsc_counts_only_resolved_correct_symbolic_predictions() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    symbolic = {
        "covered": np.array([True, False, True, True]),
        "uncovered": np.array([False, True, False, False]),
        "conflict_abstain": np.array([False, False, False, False]),
        "symbolic_class": np.array([0, -1, 0, 1], dtype=np.int8),
    }
    out = macro_correct_symbolic_coverage(y, symbolic)
    assert out["benign_correct_symbolic_coverage"] == pytest.approx(0.5)
    assert out["attack_correct_symbolic_coverage"] == pytest.approx(0.5)
    assert out["mcsc"] == pytest.approx(0.5)


def test_lambda_one_negative_control_ignores_symbolic_state() -> None:
    left_state = migrate_r0_v2_rules(
        seed=0,
        rules=[
            _rule(
                rule_id="benign",
                condition=Condition("x", "<=", 0.5),
                consequent=0,
            )
        ],
        neural_checkpoint_sha256="checkpoint",
    )
    right_state = migrate_r0_v2_rules(
        seed=0,
        rules=[
            _rule(
                rule_id="attack",
                condition=Condition("x", ">", 0.5),
                consequent=1,
            )
        ],
        neural_checkpoint_sha256="checkpoint",
    )
    X = np.array([[0.1], [0.2], [0.8], [0.9]], dtype=np.float64)
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    neural = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)

    left = evaluate_symbolic_arm(
        seed=0,
        X=X,
        y_true=y,
        neural_probability=neural,
        feature_names=FEATURES,
        state=left_state,
        neural_weight=1.0,
    )
    right = evaluate_symbolic_arm(
        seed=0,
        X=X,
        y_true=y,
        neural_probability=neural,
        feature_names=FEATURES,
        state=right_state,
        neural_weight=1.0,
    )
    verify_lambda_one_negative_control(left, right)
    np.testing.assert_array_equal(left.fused_probability, neural)
    np.testing.assert_array_equal(right.fused_probability, neural)


def test_exact_sign_test_and_holm_are_frozen() -> None:
    assert exact_one_sided_sign_pvalue(
        positive=5,
        n_effective=5,
    ) == pytest.approx(1 / 32)
    adjusted = holm_bonferroni({"a": 0.01, "b": 0.02, "c": 0.04})
    assert adjusted == pytest.approx({"a": 0.03, "b": 0.04, "c": 0.04})


def test_paired_summary_requires_five_and_preserves_all_effects() -> None:
    summary = paired_effect_summary(
        "endpoint",
        [0.1, 0.2, -0.1, 0.0, 0.3],
    )
    assert summary.effects == (0.1, 0.2, -0.1, 0.0, 0.3)
    assert summary.positive == 3
    assert summary.zero == 1
    assert summary.negative == 1
    assert summary.sign_test_n_effective == 4
    with pytest.raises(ValueError, match="exactly five"):
        paired_effect_summary("endpoint", [0.1, 0.2])


def test_confirmatory_family_uses_frozen_three_contrasts() -> None:
    d_mcc = {seed: 0.8 + 0.01 * seed for seed in range(5)}
    c_mcc = {seed: 0.7 + 0.01 * seed for seed in range(5)}
    d_mcsc = {seed: 0.6 + 0.01 * seed for seed in range(5)}
    c_mcsc = {seed: 0.5 + 0.01 * seed for seed in range(5)}
    p_mcsc = {seed: 0.55 + 0.01 * seed for seed in range(5)}
    family = build_confirmatory_family(
        d_drift_mcc_by_seed=d_mcc,
        c_mcc_by_seed=c_mcc,
        d_drift_mcsc_by_seed=d_mcsc,
        c_mcsc_by_seed=c_mcsc,
        d_periodic_mcsc_by_seed=p_mcsc,
    )
    assert len(family["endpoint_order"]) == 3
    assert set(family["holm_adjusted_p"]) == set(family["endpoint_order"])


def test_recovery_requires_two_consecutive_post_windows() -> None:
    pre = [
        {"row_count": 5_000, "m": 0.6, "start_index": 0},
        {"row_count": 5_000, "m": 0.7, "start_index": 5_000},
        {"row_count": 5_000, "m": 0.8, "start_index": 10_000},
    ]
    post = [
        {"row_count": 5_000, "m": 0.75, "start_index": 15_000},
        {"row_count": 5_000, "m": 0.72, "start_index": 20_000},
        {"row_count": 5_000, "m": 0.80, "start_index": 25_000},
    ]
    result = recovery_time(
        pre,
        post,
        metric_key="m",
        higher_is_better=True,
        stream_end_index=30_000,
    )
    assert result["baseline"] == pytest.approx(0.7)
    assert result["recovered"]
    assert result["recovery_clock"] == 15_000



def test_primary_symbolic_config_rejects_test_overrides() -> None:
    verify_primary_symbolic_operator_config(SymbolicOperatorConfig())
    with pytest.raises(ValueError, match="frozen configuration"):
        verify_primary_symbolic_operator_config(
            SymbolicOperatorConfig(validation_rows=4)
        )
