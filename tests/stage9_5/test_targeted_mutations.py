from __future__ import annotations

import inspect
import textwrap
from pathlib import Path
from collections.abc import Callable\nfrom typing import Any

import numpy as np
import pytest

import concept_drift_ids.cd_control_plane as control
import concept_drift_ids.cd_evidence as evidence
import concept_drift_ids.cd_shared_runner as shared_runner
import concept_drift_ids.cd_symbolic_arms as arms
import concept_drift_ids.cd_symbolic_runner as symbolic_runner
from concept_drift_ids import symbolic
from concept_drift_ids.cd_shared_runner import ControlPlaneConfig
from concept_drift_ids.cd_symbolic_arms import (
    SymbolicOpportunity,
    SymbolicValidationRecord,
)
from concept_drift_ids.cd_symbolic_lifecycle import migrate_r0_v2_rules
from concept_drift_ids.cd_symbolic_runner import SymbolicArmTrajectory
from concept_drift_ids.symbolic import Condition, Rule


def _mutated_function(
    function: Callable[..., Any],
    old: str,
    new: str,
    *,
    expected_count: int = 1,
) -> Callable[..., Any]:
    module = inspect.getmodule(function)
    assert module is not None
    source = textwrap.dedent(inspect.getsource(function))
    assert source.count(old) == expected_count, (
        f"mutation substrate drifted for {function.__module__}.{function.__name__}: "
        f"expected {expected_count} occurrence(s) of {old!r}, "
        f"found {source.count(old)}"
    )
    mutated = source.replace(old, new, expected_count)
    namespace = dict(module.__dict__)
    exec(
        compile(
            mutated,
            f"<stage9.5-mutant:{function.__module__}.{function.__name__}>",
            "exec",
        ),
        namespace,
    )
    return namespace[function.__name__]


def _trajectory(
    *,
    arm: str,
    state,
    seed: int = 0,
    shared: str = "shared",
    operator: str = "operator",
) -> SymbolicArmTrajectory:
    return SymbolicArmTrajectory(
        seed=seed,
        arm=arm,
        operator_config_sha256=operator,
        shared_identity_sha256=shared,
        initial_state=state,
        final_state=state,
        maintenance=(),
        publications=(),
    )


def _event(*, origin: int, maturity: int) -> dict[str, Any]:
    return {
        "schema_version": evidence.CONTROL_PLANE_SCHEMA_VERSION,
        "run_id": "run",
        "seed": 0,
        "arm": "shared_control_plane",
        "event_type": "test",
        "event_id": "event",
        "logical_clock": max(origin, maturity),
        "status": "test",
        "origin_index": origin,
        "maturity_index": maturity,
    }


def test_m01_maturity_boundary_mutant_killed() -> None:
    event = _event(origin=5, maturity=5)
    evidence.validate_event(event)

    mutant = _mutated_function(
        evidence.validate_event,
        "if maturity is not None and int(maturity) < int(origin or 0):",
        "if maturity is not None and int(maturity) <= int(origin or 0):",
    )
    with pytest.raises(ValueError, match="maturity_index"):
        mutant(event)


def test_m02_publication_boundary_mutant_killed() -> None:
    chain = (
        {"publication_effective_index": 0, "checkpoint_file_sha256": "initial"},
        {"publication_effective_index": 5, "checkpoint_file_sha256": "child"},
    )
    assert (
        symbolic_runner._checkpoint_at_next_prediction(chain, 4)[
            "checkpoint_file_sha256"
        ]
        == "child"
    )

    mutant = _mutated_function(
        symbolic_runner._checkpoint_at_next_prediction,
        'if int(record["publication_effective_index"]) <= target',
        'if int(record["publication_effective_index"]) < target',
    )
    assert mutant(chain, 4)["checkpoint_file_sha256"] == "initial"


def test_m03_prediction_label_order_mutant_killed() -> None:
    queue = control.DelayedLabelQueue(latency=1)
    queue.commit_prediction(
        row_id="r0",
        origin_index=0,
        checkpoint_sha256="checkpoint",
        neural_probability=0.2,
        true_label=0,
    )
    with pytest.raises(RuntimeError, match="prediction"):
        queue.release_after_prediction(1)

    mutant = _mutated_function(
        control.DelayedLabelQueue.release_after_prediction,
        "if logical_clock not in self._committed_clocks:",
        "if False:",
    )
    released = mutant(queue, 1)
    assert [item.row_id for item in released] == ["r0"]


def test_m04_boundary_mask_removal_mutant_killed() -> None:
    payload = {"adaptive": {"synthetic_boundary": 69_260}}
    with pytest.raises(ValueError, match="boundary"):
        control.assert_no_boundary_contamination(payload)

    mutant = _mutated_function(
        control.assert_no_boundary_contamination,
        "if normalized in PROHIBITED_ADAPTIVE_KEYS:",
        "if False:",
    )
    mutant(payload)


def test_m05_checkpoint_identity_bypass_mutant_killed() -> None:
    observation = control.DetectorObservation(
        row_id="r0",
        origin_index=0,
        maturity_index=1,
        epoch_id=1,
        epoch_checkpoint_sha256="epoch",
        prediction_checkpoint_sha256="other",
        error=1,
        admitted=True,
        drift_detected=False,
        reason="test",
    )
    with pytest.raises(ValueError, match="Checkpoint-impure"):
        control.verify_checkpoint_purity([observation])

    mutant = _mutated_function(
        control.verify_checkpoint_purity,
        "if observation.admitted and (",
        "if False and (",
    )
    mutant([observation])


def test_m06_seed_r0_threshold_bypass_mutant_killed() -> None:
    state_a = migrate_r0_v2_rules(
        seed=0,
        rules=[],
        neural_checkpoint_sha256="checkpoint-a",
    )
    divergent_rule = Rule(
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
    state_b = migrate_r0_v2_rules(
        seed=0,
        rules=[divergent_rule],
        neural_checkpoint_sha256="checkpoint-a",
    )

    seed_mutant = _mutated_function(
        symbolic_runner.verify_symbolic_arm_control_plane_isolation,
        "if len(seeds) != 1:",
        "if False:",
    )
    seed_left = _trajectory(arm="c_frozen_symbolic", state=state_a, seed=0)
    seed_right = _trajectory(arm="d_drift", state=state_a, seed=1)
    with pytest.raises(ValueError, match="different seeds"):
        symbolic_runner.verify_symbolic_arm_control_plane_isolation(
            [seed_left, seed_right]
        )
    seed_mutant([seed_left, seed_right])

    r0_mutant = _mutated_function(
        symbolic_runner.verify_symbolic_arm_control_plane_isolation,
        "if len(initial_hashes) != 1:",
        "if False:",
    )
    r0_left = _trajectory(arm="c_frozen_symbolic", state=state_a)
    r0_right = _trajectory(arm="d_drift", state=state_b)
    with pytest.raises(ValueError, match="R0.v2 starting state"):
        symbolic_runner.verify_symbolic_arm_control_plane_isolation(
            [r0_left, r0_right]
        )
    r0_mutant([r0_left, r0_right])

    threshold_mutant = _mutated_function(
        shared_runner.verify_primary_control_plane_configuration,
        "if float(monitor_threshold) != float(expected):",
        "if False:",
    )
    wrong_threshold = control.SYSTEM_A_MONITOR_THRESHOLDS[1]
    with pytest.raises(ValueError, match="Monitor threshold"):
        shared_runner.verify_primary_control_plane_configuration(
            seed=0,
            monitor_threshold=wrong_threshold,
            anchor_row_count=control.PRIMARY_ANCHOR_CAPACITY,
            config=ControlPlaneConfig(),
        )
    threshold_mutant(
        seed=0,
        monitor_threshold=wrong_threshold,
        anchor_row_count=control.PRIMARY_ANCHOR_CAPACITY,
        config=ControlPlaneConfig(),
    )


def test_m07_generation_validation_overlap_bypass_mutant_killed() -> None:
    generation = ("overlap",) + tuple(
        f"g-{index}" for index in range(9_999)
    )
    transaction = arms.open_symbolic_transaction(
        SymbolicOpportunity(
            arm="d_drift",
            opportunity_id=1,
            source="drift",
            logical_clock=10,
            shared_neural_checkpoint_sha256="checkpoint",
        ),
        neural_checkpoint_sha256="checkpoint",
        checkpoint_publication_effective_index=0,
        generation_row_ids=generation,
        generation_evidence_id="generation",
        candidates=(),
        validation_start_index=0,
    )
    records = (
        SymbolicValidationRecord(
            row_id="overlap",
            origin_index=0,
            maturity_index=0,
            neural_checkpoint_sha256="checkpoint",
            features=np.asarray([0.0], dtype=np.float32),
            true_label=0,
            neural_decision=0,
        ),
        SymbolicValidationRecord(
            row_id="independent",
            origin_index=1,
            maturity_index=1,
            neural_checkpoint_sha256="checkpoint",
            features=np.asarray([1.0], dtype=np.float32),
            true_label=1,
            neural_decision=1,
        ),
    )
    production = arms.collect_independent_validation_block(
        records,
        transaction,
        superseding_checkpoint_effective_index=None,
        required_rows=1,
    )
    assert production.row_ids == ("independent",)

    mutant = _mutated_function(
        arms.collect_independent_validation_block,
        "if record.row_id in generation:",
        "if False:",
    )
    mutated = mutant(
        records,
        transaction,
        superseding_checkpoint_effective_index=None,
        required_rows=1,
    )
    assert mutated.row_ids == ("overlap",)


def test_m08_opportunity_budget_mutants_killed() -> None:
    opportunity = SymbolicOpportunity(
        arm="d_drift",
        opportunity_id=5,
        source="drift",
        logical_clock=1,
        shared_neural_checkpoint_sha256="checkpoint",
    )
    generation = tuple(f"g-{index}" for index in range(10_000))
    with pytest.raises(ValueError, match="four-slot budget"):
        arms.open_symbolic_transaction(
            opportunity,
            neural_checkpoint_sha256="checkpoint",
            checkpoint_publication_effective_index=0,
            generation_row_ids=generation,
            generation_evidence_id="generation",
            candidates=(),
        )

    open_mutant = _mutated_function(
        arms.open_symbolic_transaction,
        "if not 1 <= opportunity.opportunity_id <= PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET:",
        "if not 1 <= opportunity.opportunity_id <= PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET + 1:",
    )
    assert (
        open_mutant(
            opportunity,
            neural_checkpoint_sha256="checkpoint",
            checkpoint_publication_effective_index=0,
            generation_row_ids=generation,
            generation_evidence_id="generation",
            candidates=(),
        ).opportunity_id
        == 5
    )

    events = [
        {
            "event_type": "drift_event",
            "status": "confirmed",
            "logical_clock": index,
            "event_id": f"e-{index}",
            "neural_checkpoint_sha256": "checkpoint",
        }
        for index in range(1, 6)
    ]
    assert len(arms.drift_symbolic_opportunities(events)) == 4
    drift_mutant = _mutated_function(
        arms.drift_symbolic_opportunities,
        "confirmed[:PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET]",
        "confirmed[:PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET + 1]",
    )
    assert len(drift_mutant(events)) == 5


def test_m09_lambda1_symbolic_contribution_mutant_killed() -> None:
    neural = np.asarray([0.2, 0.8], dtype=np.float64)
    symbolic_payload = {
        "covered": np.asarray([True, True]),
        "p_rule_attack": np.asarray([1.0, 0.0], dtype=np.float64),
    }
    production = symbolic.fuse_scores(
        neural,
        symbolic_payload,
        neural_weight=1.0,
    )
    assert np.array_equal(production, neural)

    mutant = _mutated_function(
        symbolic.fuse_scores,
        "(1 - neural_weight) * rule_score[covered]",
        "(1.1 - neural_weight) * rule_score[covered]",
    )
    mutated = mutant(
        neural,
        symbolic_payload,
        neural_weight=1.0,
    )
    assert not np.array_equal(mutated, neural)


def test_m10_manifest_hash_bypass_mutant_killed(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    path.write_text('{"value":1}\n', encoding="utf-8")
    manifest = {
        "files": {
            "evidence": {
                "path": "evidence.json",
                "sha256": "0" * 64,
            }
        }
    }
    with pytest.raises(ValueError, match="hash mismatch"):
        evidence.verify_manifest_files(tmp_path, manifest)

    mutant = _mutated_function(
        evidence.verify_manifest_files,
        "if actual != expected:",
        "if False:",
    )
    mutant(tmp_path, manifest)


def test_m11_shared_neural_identity_bypass_mutant_killed() -> None:
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[],
        neural_checkpoint_sha256="checkpoint",
    )
    left = _trajectory(
        arm="c_frozen_symbolic",
        state=state,
        shared="shared-a",
    )
    right = _trajectory(
        arm="d_drift",
        state=state,
        shared="shared-b",
    )
    with pytest.raises(ValueError, match="control-plane identity"):
        symbolic_runner.verify_symbolic_arm_control_plane_isolation(
            [left, right]
        )

    mutant = _mutated_function(
        symbolic_runner.verify_symbolic_arm_control_plane_isolation,
        "if len(shared_hashes) != 1 or not next(iter(shared_hashes)):",
        "if False:",
    )
    result = mutant([left, right])
    assert isinstance(result, str) and len(result) == 64
