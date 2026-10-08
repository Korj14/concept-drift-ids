from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
import torch

from concept_drift_ids.cd_symbolic_arms import (
    SymbolicOperatorConfig,
)
from concept_drift_ids.cd_symbolic_evidence import (
    maintenance_event_payload,
    rule_base_version_payload,
    verify_version_parent_chain,
    write_symbolic_maintenance_new,
)
from concept_drift_ids.cd_symbolic_evaluation import (
    evaluate_dynamic_symbolic_trajectory,
)
from concept_drift_ids.cd_symbolic_lifecycle import (
    OnlineRuleGate,
    migrate_r0_v2_rules,
)
from concept_drift_ids.cd_symbolic_runner import (
    SharedSymbolicRow,
    run_drift_symbolic_arm,
    verify_shared_symbolic_rows,
)
from concept_drift_ids.neural import BinaryMLP
from concept_drift_ids.symbolic import Condition, Rule


def _rule() -> Rule:
    return Rule(
        rule_id="r0",
        lineage_id="r0",
        rule_base_version="R0.v2",
        seed=0,
        conditions=(Condition("x", "<=", 0.5),),
        consequent=0,
        confidence=1.0,
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


def _toy_model() -> BinaryMLP:
    torch.manual_seed(3)
    return BinaryMLP(
        input_features=1,
        hidden_layers=(2,),
        dropout=0.0,
    )


def test_shared_symbolic_row_view_must_match_frozen_predictions() -> None:
    rows = [
        SharedSymbolicRow(
            row_id="r0",
            origin_index=0,
            maturity_index=5,
            features=np.array([0.0], dtype=np.float32),
            true_label=0,
            neural_probability=0.1,
            neural_checkpoint_sha256="a",
        )
    ]
    predictions = [
        {
            "row_id": "r0",
            "origin_index": 0,
            "maturity_index": 5,
            "checkpoint_sha256": "a",
            "neural_probability": 0.1,
        }
    ]
    verify_shared_symbolic_rows(rows, predictions)
    bad = [dict(predictions[0], neural_probability=0.2)]
    with pytest.raises(ValueError, match="neural score"):
        verify_shared_symbolic_rows(rows, bad)


def test_drift_arm_can_complete_staleness_without_candidate_generation() -> None:
    initial = migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()],
        neural_checkpoint_sha256="initial",
    )
    generation_rows = [
        SharedSymbolicRow(
            row_id=f"g-{i}",
            origin_index=i,
            maturity_index=i,
            features=np.array([0.0], dtype=np.float32),
            true_label=0,
            neural_probability=0.1,
            neural_checkpoint_sha256="initial",
        )
        for i in range(10_000)
    ]
    validation_rows = [
        SharedSymbolicRow(
            row_id=f"v-{i}",
            origin_index=10_000 + i,
            maturity_index=10_000 + i,
            features=np.array([0.0 if i < 2 else 1.0], dtype=np.float32),
            true_label=i % 2,
            neural_probability=0.1 if i % 2 == 0 else 0.9,
            neural_checkpoint_sha256="child",
        )
        for i in range(4)
    ]
    rows = generation_rows + validation_rows
    shared_events = [
        {
            "event_type": "drift_event",
            "status": "confirmed",
            "event_id": "drift-1",
            "logical_clock": 9_999,
            "neural_checkpoint_sha256": "initial",
        }
    ]
    replay_transactions = [
        {
            "event_id": 1,
            "current_row_ids": [row.row_id for row in generation_rows],
            "child_checkpoint_sha256": "child",
            "publication_effective_index": 10_000,
        }
    ]
    checkpoint_chain = [
        {
            "sequence": 0,
            "checkpoint_file_sha256": "initial",
            "publication_effective_index": 0,
        },
        {
            "sequence": 1,
            "checkpoint_file_sha256": "child",
            "publication_effective_index": 10_000,
        },
    ]
    gate = OnlineRuleGate(
        min_support=0.0,
        min_covered=1,
        min_class_precision=0.0,
        min_precision_lcb=0.0,
        min_neural_fidelity=0.0,
        min_fidelity_lcb=0.0,
        min_stability=0.0,
        max_complexity=4,
        bootstrap_replicates=2,
    )
    operator = SymbolicOperatorConfig(
        gate=gate,
        validation_rows=4,
    )
    model = _toy_model()

    trajectory = run_drift_symbolic_arm(
        seed=0,
        initial_state=initial,
        shared_events=shared_events,
        replay_transactions=replay_transactions,
        checkpoint_chain=checkpoint_chain,
        rows=rows,
        feature_names=("x",),
        model_resolver=lambda _: model,
        operator_config=operator,
    )
    assert len(trajectory.maintenance) == 1
    record = trajectory.maintenance[0]
    assert "candidate_generation_insufficient_class_evidence" in record.status
    assert record.generation_row_ids == tuple(
        row.row_id for row in generation_rows
    )
    assert len(record.validation_row_ids) == 4
    assert trajectory.operator_config_sha256 == operator.sha256()


def test_dynamic_evaluation_switches_rule_state_by_effective_index() -> None:
    initial = migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()],
        neural_checkpoint_sha256="initial",
    )
    attack_rule = Rule(
        rule_id="attack",
        lineage_id="attack",
        rule_base_version="R0.v2",
        seed=0,
        conditions=(Condition("x", ">", 0.5),),
        consequent=1,
        confidence=1.0,
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
    later = migrate_r0_v2_rules(
        seed=0,
        rules=[attack_rule],
        neural_checkpoint_sha256="child",
    )
    trajectory = SimpleNamespace(
        seed=0,
        publications=((2, later),),
        state_for_prediction_index=lambda index: (
            initial if index < 2 else later
        ),
    )
    X = np.array([[0.1], [0.2], [0.8], [0.9]], dtype=np.float64)
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    neural = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)
    evaluated = evaluate_dynamic_symbolic_trajectory(
        seed=0,
        X=X,
        y_true=y,
        neural_probability=neural,
        feature_names=("x",),
        trajectory=trajectory,
        neural_weight=0.5,
    )
    assert evaluated.covered.tolist() == [True, True, True, True]
    assert evaluated.symbolic_class.tolist() == [0, 0, 1, 1]
    assert evaluated.explanation["mcsc"] == pytest.approx(1.0)


def test_symbolic_evidence_is_write_once_for_published_result(
    tmp_path,
) -> None:
    from concept_drift_ids.cd_symbolic_arms import (
        PendingSymbolicTransaction,
        SymbolicTransactionResult,
        ValidationBlockResult,
    )
    from concept_drift_ids.cd_symbolic_lifecycle import (
        OnlineRuleGate,
        apply_lifecycle_maintenance,
    )

    parent = migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()],
        neural_checkpoint_sha256="initial",
    )
    X = np.array([[0.0], [0.1], [0.8], [0.9]], dtype=np.float64)
    y = np.array([1, 1, 0, 0], dtype=np.int8)
    neural = y.copy()
    lifecycle = apply_lifecycle_maintenance(
        parent,
        candidates=[],
        X_validation=X,
        y_validation=y,
        neural_decision=neural,
        feature_names=("x",),
        opportunity_id=1,
        validation_evidence_id="validation",
        neural_checkpoint_sha256="child-checkpoint",
        publication_effective_index=20,
        bootstrap_random_state=1,
        gate=OnlineRuleGate(
            min_support=0.0,
            min_covered=1,
            min_class_precision=0.75,
            min_precision_lcb=0.0,
            min_neural_fidelity=0.75,
            min_fidelity_lcb=0.0,
            min_stability=0.0,
            max_complexity=4,
            bootstrap_replicates=2,
        ),
    )
    assert lifecycle.published
    child = lifecycle.state
    transaction = PendingSymbolicTransaction(
        arm="d_drift",
        opportunity_id=1,
        opportunity_clock=10,
        neural_checkpoint_sha256="child-checkpoint",
        checkpoint_publication_effective_index=11,
        generation_row_ids=tuple(f"g-{i}" for i in range(10_000)),
        generation_evidence_id="generation",
        candidates=(),
        operator_config_sha256="operator",
    )
    validation = ValidationBlockResult(status="complete", records=())
    result = SymbolicTransactionResult(
        status="published",
        opportunity_id=1,
        validation_row_ids=(),
        lifecycle=lifecycle,
    )

    # The payload builder must preserve both inference and history identities.
    event = maintenance_event_payload(
        run_id="run",
        seed=0,
        arm="d_drift",
        transaction=transaction,
        validation=validation,
        result=result,
        parent_rule_base_version_id=parent.rule_base_version_id,
        parent_rule_base_sha256=parent.canonical_sha256,
        git_commit="deadbeef",
    )
    assert event["published"] is True
    assert event["result_history_sha256"] == child.history_sha256

    # A version payload requires a published D version and preserves its parent.
    payload = rule_base_version_payload(
        child,
        maintenance_event_sha256=event["maintenance_event_sha256"],
        neural_checkpoint_sha256="child-checkpoint",
        valid_from=20,
        git_commit="deadbeef",
    )
    assert payload["parent_rule_base_version_id"] == parent.rule_base_version_id

    out = tmp_path / "symbolic"
    write_symbolic_maintenance_new(
        out,
        run_id="run",
        seed=0,
        arm="d_drift",
        transaction=transaction,
        validation=validation,
        result=result,
        parent_state=parent,
        git_commit="deadbeef",
        publication_effective_index=20,
    )
    with pytest.raises(FileExistsError, match="overwrite"):
        write_symbolic_maintenance_new(
            out,
            run_id="run",
            seed=0,
            arm="d_drift",
            transaction=transaction,
            validation=validation,
            result=result,
            parent_state=parent,
            git_commit="deadbeef",
            publication_effective_index=20,
        )


def test_symbolic_version_parent_chain_rejects_divergence() -> None:
    versions = [
        {
            "version_number": 1,
            "rule_base_version_id": "v1",
            "parent_rule_base_version_id": "r0",
            "parent_rule_base_sha256": "r0hash",
            "canonical_rule_base_sha256": "h1",
        },
        {
            "version_number": 2,
            "rule_base_version_id": "v2",
            "parent_rule_base_version_id": "v1",
            "parent_rule_base_sha256": "h1",
            "canonical_rule_base_sha256": "h2",
        },
    ]
    verify_version_parent_chain(versions)
    broken = [versions[0], dict(versions[1], parent_rule_base_sha256="wrong")]
    with pytest.raises(ValueError, match="parent hash"):
        verify_version_parent_chain(broken)


def test_stage7_runtime_modules_have_no_primary_scenario_loader_surface() -> None:
    import concept_drift_ids.cd_r0_lifecycle as r0
    import concept_drift_ids.cd_symbolic_arms as arms
    import concept_drift_ids.cd_symbolic_candidates as candidates
    import concept_drift_ids.cd_symbolic_evaluation as evaluation
    import concept_drift_ids.cd_symbolic_lifecycle as lifecycle
    import concept_drift_ids.cd_symbolic_runner as runner

    modules = (r0, arms, candidates, evaluation, lifecycle, runner)
    forbidden = ("scenario_loader", "load_partition", "pre_drift", "post_drift")
    for module in modules:
        path = module.__file__
        assert path is not None
        text = open(path, encoding="utf-8").read()
        for token in forbidden:
            assert token not in text
