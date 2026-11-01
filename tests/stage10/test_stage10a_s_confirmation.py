"""S independent-confirmation operator tests; no treatment, no original models."""
from __future__ import annotations
import numpy as np
import pytest
from concept_drift_ids.cd_symbolic_arms import SymbolicValidationRecord
from concept_drift_ids.cd_symbolic_lifecycle import CandidateRule, OnlineRuleGate
from concept_drift_ids.stage10a_s_confirmation import confirm_selected_candidates
from concept_drift_ids.symbolic import Condition


def _args():
    rule = CandidateRule(
        candidate_id="prevalidated-0", seed=0,
        conditions=(Condition("f0", "<=", 0.5),),
        consequent=0, generation_evidence_id="gen-test"
    )
    rows = tuple(
        SymbolicValidationRecord(
            row_id=f"confirmation-{i}", origin_index=101+i,
            maturity_index=5101+i, neural_checkpoint_sha256="a"*64,
            features=np.asarray([0 if i%2==0 else 1], dtype=np.float32),
            true_label=i%2, neural_decision=i%2,
        ) for i in range(4)
    )
    gate = OnlineRuleGate(
        min_support=0.1, min_covered=1, min_class_precision=0,
        min_precision_lcb=0, min_neural_fidelity=0,
        min_fidelity_lcb=0, min_stability=0, bootstrap_replicates=1
    )
    return dict(
        selected=[rule],
        generation_ids=["gen-0"],
        confirmed_selection_validation_ids=["selection-0"],
        selection_completion_clock=100,
        confirmation_records=rows,
        checkpoint_sha256="a"*64,
        next_checkpoint_effective_index=None,
        feature_names=["f0"], seed=0, opportunity_id=1,
        required_rows=4, gate=gate,
    )


def test_real_s_operator_requires_future_mature_disjoint_block():
    result=confirm_selected_candidates(**_args())
    assert result.status=="independently_confirmed_subset"
    assert result.publication_effective_index==5105
    assert len(result.row_ids)==4
    assert result.candidate_evidence[0]["independently_confirmed"] is True


def test_no_confirmation_before_selection_completes():
    kw=_args()
    kw["selection_completion_clock"]=103
    result=confirm_selected_candidates(**kw)
    assert result.status=="right_censored_confirmation"
    assert result.publication_effective_index is None


def test_supersession_censors_without_publication():
    kw=_args()
    kw["next_checkpoint_effective_index"]=5103
    result=confirm_selected_candidates(**kw)
    assert result.status=="superseded_before_confirmation"
    assert result.publication_effective_index is None


def test_overlap_or_early_label_violation_stops():
    kw=_args()
    kw["confirmed_selection_validation_ids"]=["confirmation-0"]
    with pytest.raises(ValueError, match="duplicates/leaks"):
        confirm_selected_candidates(**kw)
    kw=_args()
    bad=kw["confirmation_records"][0]
    from dataclasses import replace
    kw["confirmation_records"]=(replace(bad,maturity_index=5100),*kw["confirmation_records"][1:])
    with pytest.raises(ValueError,match="maturity"):
        confirm_selected_candidates(**kw)


def test_complete_with_no_class_diversity_cannot_confirm():
    kw=_args()
    from dataclasses import replace
    kw["confirmation_records"]=tuple(replace(r,true_label=0) for r in kw["confirmation_records"])
    result=confirm_selected_candidates(**kw)
    assert result.status=="insufficient_confirmation_class_diversity"
    assert not result.candidate_evidence and result.publication_effective_index is None
