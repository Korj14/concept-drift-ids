"""Read-only S-confirm Phase-B integration contract; NO real treatment."""
import numpy as np
import pytest
from concept_drift_ids.cd_symbolic_lifecycle import migrate_r0_v2_rules
from concept_drift_ids.cd_symbolic_runner import SharedSymbolicRow
from concept_drift_ids.stage10a_s_phase_b import run_s_confirmation_arm
from concept_drift_ids.symbolic import Condition, Rule


def _test_arm():
    r=Rule(
        rule_id="r0",lineage_id="r0",rule_base_version="R0.v2",seed=0,
        conditions=(Condition("f0","<=",0.5),),consequent=0,
        confidence=1,support=.5,covered_count=50,class_precision=1,
        neural_fidelity=1,stability=1,complexity=1,lifecycle_state="active",
        source_candidate_id="historical",validation_evidence_id="historical",
    )
    state=migrate_r0_v2_rules(
        seed=0,rules=[r],neural_checkpoint_sha256="a"*64
    )
    rows=[
        SharedSymbolicRow(
            row_id=f"stage10a-logical-{i:06d}",origin_index=i,
            maturity_index=i+5000,features=np.zeros(1,dtype=np.float32),
            true_label=i%2,neural_probability=0.1,
            neural_checkpoint_sha256="a"*64,
        ) for i in range(2)
    ]
    predictions=[dict(
        row_id=x.row_id,origin_index=x.origin_index,
        maturity_index=x.maturity_index,
        checkpoint_sha256=x.neural_checkpoint_sha256,
        neural_probability=x.neural_probability,
    ) for x in rows]
    return dict(
        seed=0,source_arm="d_drift",initial_state=state,
        shared_identity_sha256="sealed-shared-test",
        shared_predictions=predictions,shared_events=[],
        replay_transactions=[],checkpoint_chain=[
            dict(checkpoint_file_sha256="a"*64,publication_effective_index=0)
        ],rows=rows,feature_names=["f0"],
        model_resolver=lambda _: pytest.fail("A model was loaded"),
    )


def test_no_drift_means_no_spurious_s_rule_and_no_checkpoint_load():
    kw=_test_arm()
    r=run_s_confirmation_arm(**kw)
    assert r.publications==() and r.opportunities==()
    assert r.final_state.canonical_sha256==kw["initial_state"].canonical_sha256
    assert r.prospective_s_method_frozen is False
    assert r.stage10a_release_authorized is False


def test_unsealed_prediction_identity_rejected():
    kw=_test_arm()
    kw["shared_predictions"][0]["neural_probability"]=0.7
    with pytest.raises(ValueError,match="neural score"):
        run_s_confirmation_arm(**kw)


def test_no_neural_replay_for_drift_cannot_publish():
    kw=_test_arm()
    kw["shared_events"]=[{
        "event_type":"drift_event","status":"confirmed","event_id":"e1",
        "logical_clock":1,"neural_checkpoint_sha256":"a"*64
    }]
    r=run_s_confirmation_arm(**kw)
    assert len(r.opportunities)==1
    assert r.opportunities[0].status=="blocked_no_neural_child"
    assert r.publications==()


def test_wrong_arm_fails_before_loading_checkpoint():
    kw=_test_arm()
    kw["source_arm"]="s_confirm_fake"
    with pytest.raises(ValueError,match="seed/arm"):
        run_s_confirmation_arm(**kw)
