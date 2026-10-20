from __future__ import annotations

import numpy as np
import pytest

from concept_drift_ids.cd_control_plane import (
    PRIMARY_ANCHOR_CAPACITY,
    SYSTEM_A_MONITOR_THRESHOLDS,
    DelayedLabelQueue,
    DetectorObservation,
    assert_no_boundary_contamination,
    verify_checkpoint_purity,
    verify_information_timing,
    verify_shared_control_plane_identity,
    write_json_new,
)
from concept_drift_ids.cd_evidence import build_event, write_jsonl_new
from concept_drift_ids.cd_shared_runner import (
    ControlPlaneConfig,
    verify_primary_control_plane_configuration,
)
from concept_drift_ids.cd_symbolic_arms import (
    SymbolicOperatorConfig,
    SymbolicOpportunity,
    SymbolicValidationRecord,
    ValidationBlockResult,
    complete_symbolic_transaction,
    open_symbolic_transaction,
)
from concept_drift_ids.cd_symbolic_candidates import symbolic_seed_base
from concept_drift_ids.cd_symbolic_evaluation import (
    SymbolicArmEvaluation,
    verify_lambda_one_negative_control,
)
from concept_drift_ids.cd_symbolic_lifecycle import migrate_r0_v2_rules
from concept_drift_ids.cd_symbolic_runner import (
    SymbolicArmTrajectory,
    verify_symbolic_arm_control_plane_isolation,
)
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


def _state(*, with_rule: bool = False):
    return migrate_r0_v2_rules(
        seed=0,
        rules=[_rule()] if with_rule else [],
        neural_checkpoint_sha256="initial",
    )


def _trajectory(
    *,
    arm: str,
    state=None,
    seed: int = 0,
    shared: str = "shared",
    operator: str = "operator",
) -> SymbolicArmTrajectory:
    initial = _state() if state is None else state
    return SymbolicArmTrajectory(
        seed=seed,
        arm=arm,
        operator_config_sha256=operator,
        shared_identity_sha256=shared,
        initial_state=initial,
        final_state=initial,
        maintenance=(),
        publications=(),
    )


def _evaluation(
    neural: np.ndarray,
    fused: np.ndarray,
    decisions: np.ndarray,
) -> SymbolicArmEvaluation:
    n = len(neural)
    return SymbolicArmEvaluation(
        neural_probability=np.asarray(neural, dtype=np.float64),
        symbolic_attack_probability=np.zeros(n, dtype=np.float64),
        symbolic_class=np.full(n, -1, dtype=np.int8),
        covered=np.zeros(n, dtype=bool),
        uncovered=np.ones(n, dtype=bool),
        conflict_abstain=np.zeros(n, dtype=bool),
        fused_probability=np.asarray(fused, dtype=np.float64),
        thresholded_decision=np.asarray(decisions, dtype=np.int8),
        metrics={},
        explanation={},
    )


def test_p01_label_release_before_prediction_fails_closed() -> None:
    queue = DelayedLabelQueue(latency=1)
    with pytest.raises(RuntimeError, match="prediction"):
        queue.release_after_prediction(0)


def test_p02_detector_observation_before_label_maturity_fails_closed() -> None:
    with pytest.raises(ValueError, match="Pending label"):
        verify_information_timing(
            [
                {
                    "logical_clock": 7,
                    "origin_index": 4,
                    "maturity_index": 8,
                    "label_required": True,
                }
            ]
        )


def test_p03_boundary_reference_contamination_fails_closed() -> None:
    with pytest.raises(ValueError, match="boundary"):
        assert_no_boundary_contamination(
            {
                "adaptive_input": {
                    "nested": {
                        "synthetic_boundary": 69_260,
                    }
                }
            }
        )


def test_p04_wrong_checkpoint_detector_admission_fails_closed() -> None:
    observation = DetectorObservation(
        row_id="r0",
        origin_index=1,
        maturity_index=6,
        epoch_id=2,
        epoch_checkpoint_sha256="child",
        prediction_checkpoint_sha256="parent",
        error=1,
        admitted=True,
        drift_detected=False,
        reason="admitted",
    )
    with pytest.raises(ValueError, match="Checkpoint-impure"):
        verify_checkpoint_purity([observation])


def test_p05_shared_neural_trajectory_divergence_fails_closed() -> None:
    left = _trajectory(arm="c_frozen_symbolic", shared="shared-a")
    right = _trajectory(arm="d_drift", shared="shared-b")
    with pytest.raises(ValueError, match="control-plane identity"):
        verify_symbolic_arm_control_plane_isolation([left, right])


def test_p06_wrong_r0_start_identity_fails_closed() -> None:
    left_state = _state(with_rule=False)
    right_state = _state(with_rule=True)
    left = _trajectory(arm="c_frozen_symbolic", state=left_state)
    right = _trajectory(arm="d_drift", state=right_state)
    with pytest.raises(ValueError, match="R0.v2 starting state"):
        verify_symbolic_arm_control_plane_isolation([left, right])


def test_p07_seed_or_threshold_binding_mismatch_fails_closed() -> None:
    with pytest.raises(ValueError, match="Monitor threshold"):
        verify_primary_control_plane_configuration(
            seed=0,
            monitor_threshold=SYSTEM_A_MONITOR_THRESHOLDS[1],
            anchor_row_count=PRIMARY_ANCHOR_CAPACITY,
            config=ControlPlaneConfig(),
        )
    with pytest.raises(ValueError, match="Unsupported frozen seed"):
        verify_primary_control_plane_configuration(
            seed=99,
            monitor_threshold=SYSTEM_A_MONITOR_THRESHOLDS[0],
            anchor_row_count=PRIMARY_ANCHOR_CAPACITY,
            config=ControlPlaneConfig(),
        )


def test_p08_generation_validation_overlap_fails_closed() -> None:
    operator = SymbolicOperatorConfig(validation_rows=1)
    generation_row_ids = tuple(f"g-{index}" for index in range(10_000))
    transaction = open_symbolic_transaction(
        SymbolicOpportunity(
            arm="d_drift",
            opportunity_id=1,
            source="drift",
            logical_clock=10,
            shared_neural_checkpoint_sha256="child",
        ),
        neural_checkpoint_sha256="child",
        checkpoint_publication_effective_index=11,
        generation_row_ids=generation_row_ids,
        generation_evidence_id="generation",
        candidates=(),
        validation_start_index=11,
        operator_config=operator,
    )
    validation = ValidationBlockResult(
        status="complete",
        records=(
            SymbolicValidationRecord(
                row_id=generation_row_ids[0],
                origin_index=11,
                maturity_index=11,
                neural_checkpoint_sha256="child",
                features=np.asarray([0.0], dtype=np.float32),
                true_label=0,
                neural_decision=0,
            ),
        ),
    )
    with pytest.raises(ValueError, match="evidence overlap"):
        complete_symbolic_transaction(
            _state(),
            transaction,
            validation,
            feature_names=("x",),
            validation_evidence_id="validation",
            publication_effective_index=12,
            operator_config=operator,
        )


def test_p09_retrospective_prediction_replacement_fails_closed(
    tmp_path,
) -> None:
    path = tmp_path / "predictions.jsonl"
    original = build_event(
        run_id="run",
        seed=0,
        event_type="prediction",
        event_id="prediction-0",
        logical_clock=0,
        status="committed",
        origin_index=0,
        neural_checkpoint_sha256="checkpoint-a",
    )
    replacement = build_event(
        run_id="run",
        seed=0,
        event_type="prediction",
        event_id="prediction-0",
        logical_clock=0,
        status="committed",
        origin_index=0,
        neural_checkpoint_sha256="checkpoint-b",
    )
    write_jsonl_new(path, [original])
    with pytest.raises(FileExistsError, match="overwrite"):
        write_jsonl_new(path, [replacement])


def test_p10_treatment_dependent_detector_input_fails_closed() -> None:
    common = {
        "label_schedule_sha256": "labels",
        "detector_events_sha256": "detector-a",
        "replay_evidence_sha256": "replay",
        "checkpoint_chain_sha256": "checkpoints",
    }
    treatment_dependent = dict(common, detector_events_sha256="detector-b")
    with pytest.raises(ValueError, match="detector_events_sha256"):
        verify_shared_control_plane_identity(common, treatment_dependent)


def test_p11_symbolic_operator_or_rng_mismatch_fails_closed() -> None:
    state = _state()
    drift = _trajectory(
        arm="d_drift",
        state=state,
        operator="operator-a",
    )
    periodic_operator_mismatch = _trajectory(
        arm="d_periodic",
        state=state,
        operator="operator-b",
    )
    with pytest.raises(ValueError, match="different symbolic operators"):
        verify_symbolic_arm_control_plane_isolation(
            [drift, periodic_operator_mismatch]
        )

    assert symbolic_seed_base(0, 1) != symbolic_seed_base(1, 1)
    periodic_rng_namespace_mismatch = _trajectory(
        arm="d_periodic",
        state=state,
        seed=1,
        operator="operator-a",
    )
    with pytest.raises(ValueError, match="different seeds"):
        verify_symbolic_arm_control_plane_isolation(
            [drift, periodic_rng_namespace_mismatch]
        )


def test_p12_lambda1_symbolic_predictive_influence_fails() -> None:
    neural = np.asarray([0.2, 0.8], dtype=np.float64)
    left = _evaluation(
        neural,
        np.asarray([0.1, 0.9], dtype=np.float64),
        np.asarray([0, 1], dtype=np.int8),
    )
    right = _evaluation(
        neural,
        neural.copy(),
        np.asarray([0, 1], dtype=np.int8),
    )
    with pytest.raises(ValueError, match="fused scores"):
        verify_lambda_one_negative_control(left, right)


def test_p13_write_after_freeze_or_partial_reuse_fails_closed(
    tmp_path,
) -> None:
    frozen = tmp_path / "frozen.json"
    write_json_new(frozen, {"schema_version": 1, "value": "accepted"})
    with pytest.raises(FileExistsError, match="overwrite"):
        write_json_new(frozen, {"schema_version": 1, "value": "replacement"})

    partial = tmp_path / "partial.json"
    partial.write_text("", encoding="utf-8")
    with pytest.raises(FileExistsError, match="overwrite"):
        write_json_new(partial, {"schema_version": 1, "value": "reuse"})
