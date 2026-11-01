"""Live inherited symbolic selection bound to future-only S confirmation.

Small fixed evidence is a function test, not an experimental prediction/arm.
"""
from __future__ import annotations

from dataclasses import replace
import numpy as np
import pytest
from concept_drift_ids.cd_symbolic_arms import (
    SymbolicOpportunity, SymbolicOperatorConfig, SymbolicValidationRecord,
    ValidationBlockResult, open_symbolic_transaction,
)
from concept_drift_ids.cd_symbolic_lifecycle import (
    CandidateRule, OnlineRuleGate, migrate_r0_v2_rules,
)
from concept_drift_ids.stage10a_s_selection import validate_and_confirm_s_selection
from concept_drift_ids.symbolic import Condition, Rule


def _test_inputs():
    baseline_rule=Rule(
        rule_id="historical",lineage_id="historical",rule_base_version="R0.v2",
        seed=0,conditions=(Condition("x",">",0.5),),consequent=1,
        confidence=1,support=0.5,covered_count=50,class_precision=1,
        neural_fidelity=1,stability=1,complexity=1,lifecycle_state="active",
        source_candidate_id="historical",validation_evidence_id="old",
    )
    state=migrate_r0_v2_rules(
        seed=0,rules=[baseline_rule],neural_checkpoint_sha256="a"*64
    )
    gate=OnlineRuleGate(
        min_support=0,min_covered=1,min_class_precision=0,
        min_precision_lcb=0,min_neural_fidelity=0,min_fidelity_lcb=0,
        min_stability=0,bootstrap_replicates=1,
    )
    config=SymbolicOperatorConfig(gate=gate,validation_rows=8)
    candidate=CandidateRule(
        candidate_id="new-candidate",seed=0,
        conditions=(Condition("x","<=",0.5),),consequent=0,
        generation_evidence_id="generated",
    )
    opportunity=SymbolicOpportunity(
        arm="d_drift",opportunity_id=1,source="drift",
        logical_clock=99,shared_neural_checkpoint_sha256="a"*64,
    )
    transaction=open_symbolic_transaction(
        opportunity,neural_checkpoint_sha256="a"*64,
        checkpoint_publication_effective_index=100,
        generation_row_ids=[f"g{i}" for i in range(10000)],
        generation_evidence_id="generated",candidates=[candidate],
        operator_config=config,
    )
    def r(prefix,i,origin):
        return SymbolicValidationRecord(
            row_id=f"{prefix}{i}",origin_index=origin,
            maturity_index=origin+5000,
            neural_checkpoint_sha256="a"*64,
            features=np.array([float(i%2)],dtype=np.float32),
            true_label=i%2,neural_decision=i%2
        )
    validation=ValidationBlockResult(
        "complete",tuple(r("v",i,100+i) for i in range(8))
    )
    future=tuple(r("c",i,5200+i) for i in range(8))
    return dict(
        initial_s_state=state,transaction=transaction,validation=validation,
        confirmation_records=future,feature_names=["x"],
        operator_config=config,next_checkpoint_effective_index=None,
        required_confirmation_rows=8,
    )


def test_s_selection_is_rederived_before_independent_confirmation():
    r=validate_and_confirm_s_selection(**_test_inputs())
    assert r.selection_status=="selected_then_confirmation_evaluated"
    assert r.selected_candidate_ids==("new-candidate",)
    assert r.confirmation.status=="independently_confirmed_subset"
    assert r.confirmation.publication_effective_index==10208
    assert r.s_phase_b_rule_publication_authorized is False


def test_s_confirmation_rejects_substituted_generation_origin():
    kw=_test_inputs()
    c=kw["transaction"].candidates[0]
    kw["transaction"]=replace(kw["transaction"],candidates=(replace(
        c,generation_evidence_id="fake-generation"
    ),))
    with pytest.raises(ValueError,match="identity/operator"):
        validate_and_confirm_s_selection(**kw)


def test_s_confirmation_never_reuses_selection_rows():
    kw=_test_inputs()
    kw["confirmation_records"]=(kw["validation"].records[0],*kw["confirmation_records"])
    with pytest.raises(ValueError,match="duplicates/leaks"):
        validate_and_confirm_s_selection(**kw)


def test_s_confirmation_does_not_publish_on_supersession():
    kw=_test_inputs()
    kw["next_checkpoint_effective_index"]=5300
    r=validate_and_confirm_s_selection(**kw)
    assert r.confirmation.status=="superseded_before_confirmation"
    assert r.confirmation.publication_effective_index is None
    assert r.s_phase_b_rule_publication_authorized is False


def test_s_selection_does_not_mutate_primary_baseline():
    kw=_test_inputs()
    before=kw["initial_s_state"].canonical_sha256
    _=validate_and_confirm_s_selection(**kw)
    assert kw["initial_s_state"].canonical_sha256==before
    assert kw["initial_s_state"].version_number==0


def test_confirmed_candidate_is_delayed_into_s_rule_base():
    from concept_drift_ids.stage10a_s_selection import derive_s_delayed_rule_base
    kw=_test_inputs()
    before=kw["initial_s_state"].canonical_sha256
    result=derive_s_delayed_rule_base(**kw)
    assert result.selection.confirmation.status=="independently_confirmed_subset"
    assert result.state is not None
    assert result.valid_from==10208
    assert result.s_variant_frozen is False
    assert any(
        r.source_candidate_id=="new-candidate" and r.valid_from==10208
        for r in result.state.active_revisions()
    )
    assert kw["initial_s_state"].canonical_sha256==before


def test_unconfirmed_or_superseded_candidate_cannot_publish_s_state():
    from concept_drift_ids.stage10a_s_selection import derive_s_delayed_rule_base
    kw=_test_inputs()
    kw["next_checkpoint_effective_index"]=5300
    result=derive_s_delayed_rule_base(**kw)
    assert result.state is None and result.valid_from is None
    kw=_test_inputs()
    from dataclasses import replace
    kw["confirmation_records"]=tuple(
        replace(r,true_label=0) for r in kw["confirmation_records"]
    )
    result=derive_s_delayed_rule_base(**kw)
    assert result.state is None and result.valid_from is None


def test_historical_candidate_id_collision_is_not_reinterpreted_as_new():
    kw=_test_inputs()
    from dataclasses import replace
    candidate=kw["transaction"].candidates[0]
    kw["transaction"]=replace(
        kw["transaction"],candidates=(replace(candidate,candidate_id="historical"),)
    )
    with pytest.raises(ValueError,match="collides with historical"):
        validate_and_confirm_s_selection(**kw)
