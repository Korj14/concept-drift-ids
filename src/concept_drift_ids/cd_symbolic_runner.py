from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch
from torch import nn

from concept_drift_ids.cd_control_plane import (
    SYSTEM_A_MONITOR_THRESHOLDS,
    canonical_sha256,
)
from concept_drift_ids.cd_symbolic_arms import (
    PRIMARY_STREAM_LENGTH,
    PendingSymbolicTransaction,
    SymbolicOpportunity,
    SymbolicOperatorConfig,
    SymbolicTransactionResult,
    SymbolicValidationRecord,
    ValidationBlockResult,
    collect_independent_validation_block,
    complete_symbolic_transaction,
    drift_symbolic_opportunities,
    frozen_periodic_opportunities,
    open_symbolic_transaction,
)
from concept_drift_ids.cd_symbolic_candidates import (
    CandidateGenerationResult,
    generate_symbolic_candidates,
)
from concept_drift_ids.cd_symbolic_lifecycle import RuleBaseState


@dataclass(frozen=True)
class SharedSymbolicRow:
    row_id: str
    origin_index: int
    maturity_index: int
    features: np.ndarray
    true_label: int
    neural_probability: float
    neural_checkpoint_sha256: str


@dataclass(frozen=True)
class SymbolicMaintenanceRecord:
    arm: str
    opportunity_id: int
    opportunity_clock: int
    status: str
    neural_checkpoint_sha256: str | None
    generation_evidence_id: str | None
    generation_row_ids: tuple[str, ...]
    validation_row_ids: tuple[str, ...]
    validation_completion_clock: int | None
    symbolic_publication_effective_index: int | None
    parent_rule_base_version_id: str
    result_rule_base_version_id: str
    parent_rule_base_sha256: str
    result_rule_base_sha256: str
    history_sha256: str
    lifecycle: SymbolicTransactionResult | None


@dataclass(frozen=True)
class SymbolicArmTrajectory:
    seed: int
    arm: str
    operator_config_sha256: str
    initial_state: RuleBaseState
    final_state: RuleBaseState
    maintenance: tuple[SymbolicMaintenanceRecord, ...]
    publications: tuple[tuple[int, RuleBaseState], ...]

    def state_for_prediction_index(self, index: int) -> RuleBaseState:
        state = self.initial_state
        for effective_index, published in sorted(
            self.publications,
            key=lambda item: item[0],
        ):
            if effective_index <= index:
                state = published
            else:
                break
        return state


ModelResolver = Callable[[str], nn.Module]


def _predict_probabilities(
    model: nn.Module,
    X: np.ndarray,
    *,
    batch_size: int = 4_096,
) -> np.ndarray:
    X = np.asarray(X, dtype=np.float32)
    model = model.cpu().eval()
    out: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(X), batch_size):
            batch = torch.from_numpy(X[start : start + batch_size])
            logits = model(batch)
            out.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(out).astype(np.float64, copy=False)


def verify_shared_symbolic_rows(
    rows: Sequence[SharedSymbolicRow],
    shared_predictions: Sequence[Mapping[str, Any]],
) -> None:
    if len(rows) != len(shared_predictions):
        raise ValueError("Symbolic row view differs from shared prediction count.")
    ordered = sorted(rows, key=lambda item: item.origin_index)
    for expected, (row, prediction) in enumerate(
        zip(ordered, shared_predictions)
    ):
        if row.origin_index != expected:
            raise ValueError("Symbolic row origins are not contiguous.")
        if row.row_id != prediction["row_id"]:
            raise ValueError("Symbolic row identity differs from shared trajectory.")
        if row.maturity_index != int(prediction["maturity_index"]):
            raise ValueError("Symbolic row maturity differs from shared trajectory.")
        if (
            row.neural_checkpoint_sha256
            != prediction["checkpoint_sha256"]
        ):
            raise ValueError(
                "Symbolic row checkpoint differs from shared trajectory."
            )
        if float(row.neural_probability) != float(
            prediction["neural_probability"]
        ):
            raise ValueError(
                "Symbolic row neural score differs from shared trajectory."
            )


def _checkpoint_records(
    checkpoint_chain: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    records = tuple(
        sorted(
            checkpoint_chain,
            key=lambda item: int(item["publication_effective_index"]),
        )
    )
    if not records or int(records[0]["publication_effective_index"]) != 0:
        raise ValueError("Shared checkpoint chain lacks initial state.")
    return records


def _checkpoint_at_next_prediction(
    checkpoint_chain: Sequence[Mapping[str, Any]],
    logical_clock: int,
) -> Mapping[str, Any]:
    records = _checkpoint_records(checkpoint_chain)
    target = int(logical_clock) + 1
    eligible = [
        record
        for record in records
        if int(record["publication_effective_index"]) <= target
    ]
    if not eligible:
        raise ValueError("No shared neural checkpoint is effective.")
    return eligible[-1]


def _next_checkpoint_effective_index(
    checkpoint_chain: Sequence[Mapping[str, Any]],
    checkpoint_sha256: str,
) -> int | None:
    records = _checkpoint_records(checkpoint_chain)
    index = next(
        (
            i
            for i, record in enumerate(records)
            if str(record["checkpoint_file_sha256"])
            == str(checkpoint_sha256)
        ),
        None,
    )
    if index is None:
        raise ValueError("Checkpoint absent from shared checkpoint chain.")
    if index + 1 >= len(records):
        return None
    return int(records[index + 1]["publication_effective_index"])


def _stream_lookup(
    rows: Sequence[SharedSymbolicRow],
) -> dict[str, SharedSymbolicRow]:
    lookup: dict[str, SharedSymbolicRow] = {}
    for row in rows:
        if row.row_id in lookup:
            raise ValueError("Duplicate shared symbolic row ID.")
        lookup[row.row_id] = row
    return lookup


def _generation_arrays(
    row_ids: Sequence[str],
    lookup: Mapping[str, SharedSymbolicRow],
) -> tuple[np.ndarray, np.ndarray]:
    try:
        selected = [lookup[row_id] for row_id in row_ids]
    except KeyError as exc:
        raise ValueError(
            f"Generation row absent from shared row view: {exc.args[0]}"
        ) from exc
    X = np.stack(
        [np.asarray(row.features, dtype=np.float32) for row in selected]
    )
    y = np.asarray([row.true_label for row in selected], dtype=np.int8)
    return X, y


def _generation_result(
    *,
    model: nn.Module,
    row_ids: Sequence[str],
    lookup: Mapping[str, SharedSymbolicRow],
    feature_names: Sequence[str],
    seed: int,
    opportunity_id: int,
    raw_affine: Mapping[str, tuple[float, float]] | None,
    operator_config: SymbolicOperatorConfig,
) -> tuple[tuple[Any, ...], str, str]:
    X, y = _generation_arrays(row_ids, lookup)
    if any(int(np.sum(y == value)) < 128 for value in (0, 1)):
        evidence_id = canonical_sha256(
            {
                "seed": seed,
                "opportunity_id": opportunity_id,
                "row_ids": list(row_ids),
                "status": "candidate_generation_insufficient_class_evidence",
                "operator_config_sha256": operator_config.sha256(),
            }
        )
        return (), evidence_id, "candidate_generation_insufficient_class_evidence"

    probabilities = _predict_probabilities(model, X)
    result = generate_symbolic_candidates(
        model,
        X,
        y,
        probabilities,
        row_ids=row_ids,
        feature_names=feature_names,
        neural_threshold=SYSTEM_A_MONITOR_THRESHOLDS[seed],
        seed=seed,
        opportunity_id=opportunity_id,
        raw_affine=raw_affine,
        config=operator_config.generation,
    )
    return (
        tuple(result.candidates),
        result.generation_evidence_id,
        "candidate_generation_complete",
    )


def _validation_records(
    rows: Sequence[SharedSymbolicRow],
    *,
    neural_threshold: float,
) -> tuple[SymbolicValidationRecord, ...]:
    return tuple(
        SymbolicValidationRecord(
            row_id=row.row_id,
            origin_index=row.origin_index,
            maturity_index=row.maturity_index,
            neural_checkpoint_sha256=row.neural_checkpoint_sha256,
            features=np.asarray(row.features),
            true_label=int(row.true_label),
            neural_decision=int(
                row.neural_probability >= float(neural_threshold)
            ),
        )
        for row in rows
    )


def _complete_one(
    *,
    state: RuleBaseState,
    opportunity: SymbolicOpportunity,
    checkpoint_sha256: str,
    checkpoint_effective_index: int,
    generation_row_ids: Sequence[str],
    rows: Sequence[SharedSymbolicRow],
    lookup: Mapping[str, SharedSymbolicRow],
    model_resolver: ModelResolver,
    checkpoint_chain: Sequence[Mapping[str, Any]],
    feature_names: Sequence[str],
    seed: int,
    raw_affine: Mapping[str, tuple[float, float]] | None,
    operator_config: SymbolicOperatorConfig,
) -> tuple[RuleBaseState, SymbolicMaintenanceRecord, int]:
    parent = state
    model = model_resolver(checkpoint_sha256)
    candidates, generation_evidence_id, generation_status = _generation_result(
        model=model,
        row_ids=generation_row_ids,
        lookup=lookup,
        feature_names=feature_names,
        seed=seed,
        opportunity_id=opportunity.opportunity_id,
        raw_affine=raw_affine,
        operator_config=operator_config,
    )
    transaction = open_symbolic_transaction(
        opportunity,
        neural_checkpoint_sha256=checkpoint_sha256,
        checkpoint_publication_effective_index=checkpoint_effective_index,
        generation_row_ids=generation_row_ids,
        generation_evidence_id=generation_evidence_id,
        candidates=candidates,
        operator_config=operator_config,
    )
    supersession = _next_checkpoint_effective_index(
        checkpoint_chain,
        checkpoint_sha256,
    )
    validation = collect_independent_validation_block(
        _validation_records(
            rows,
            neural_threshold=SYSTEM_A_MONITOR_THRESHOLDS[seed],
        ),
        transaction,
        superseding_checkpoint_effective_index=supersession,
        required_rows=operator_config.validation_rows,
    )

    if validation.status == "complete":
        completion_clock = max(
            record.maturity_index for record in validation.records
        )
        publication_effective_index = completion_clock + 1
        if (
            supersession is not None
            and publication_effective_index >= supersession
        ):
            validation = ValidationBlockResult(
                status="superseded_before_symbolic_publication",
                records=validation.records,
            )
    else:
        completion_clock = (
            supersession
            if validation.status == "superseded_before_validation"
            else max(
                (record.maturity_index for record in validation.records),
                default=None,
            )
        )
        publication_effective_index = None

    validation_evidence_id = canonical_sha256(
        {
            "seed": seed,
            "arm": opportunity.arm,
            "opportunity_id": opportunity.opportunity_id,
            "checkpoint_sha256": checkpoint_sha256,
            "row_ids": list(validation.row_ids),
            "status": validation.status,
        }
    )
    completed = complete_symbolic_transaction(
        state,
        transaction,
        validation,
        feature_names=feature_names,
        validation_evidence_id=validation_evidence_id,
        publication_effective_index=(
            publication_effective_index
            if publication_effective_index is not None
            else max(
                checkpoint_effective_index,
                int(completion_clock or checkpoint_effective_index),
            )
            + 1
        ),
        operator_config=operator_config,
    )

    next_state = (
        completed.lifecycle.state
        if completed.lifecycle is not None
        else state
    )
    effective = (
        publication_effective_index
        if completed.lifecycle is not None
        and completed.lifecycle.published
        else None
    )
    status = completed.status
    if (
        generation_status
        == "candidate_generation_insufficient_class_evidence"
        and completed.lifecycle is not None
    ):
        status = (
            f"{status};candidate_generation_insufficient_class_evidence"
        )

    record = SymbolicMaintenanceRecord(
        arm=opportunity.arm,
        opportunity_id=opportunity.opportunity_id,
        opportunity_clock=opportunity.logical_clock,
        status=status,
        neural_checkpoint_sha256=checkpoint_sha256,
        generation_evidence_id=generation_evidence_id,
        generation_row_ids=tuple(generation_row_ids),
        validation_row_ids=validation.row_ids,
        validation_completion_clock=(
            int(completion_clock)
            if completion_clock is not None
            else None
        ),
        symbolic_publication_effective_index=effective,
        parent_rule_base_version_id=parent.rule_base_version_id,
        result_rule_base_version_id=next_state.rule_base_version_id,
        parent_rule_base_sha256=parent.canonical_sha256,
        result_rule_base_sha256=next_state.canonical_sha256,
        history_sha256=next_state.history_sha256,
        lifecycle=completed,
    )
    pending_until = (
        int(completion_clock)
        if completion_clock is not None
        else PRIMARY_STREAM_LENGTH
    )
    return next_state, record, pending_until


def run_drift_symbolic_arm(
    *,
    seed: int,
    initial_state: RuleBaseState,
    shared_events: Sequence[Mapping[str, Any]],
    replay_transactions: Sequence[Mapping[str, Any]],
    checkpoint_chain: Sequence[Mapping[str, Any]],
    rows: Sequence[SharedSymbolicRow],
    feature_names: Sequence[str],
    model_resolver: ModelResolver,
    raw_affine: Mapping[str, tuple[float, float]] | None = None,
    operator_config: SymbolicOperatorConfig = SymbolicOperatorConfig(),
) -> SymbolicArmTrajectory:
    lookup = _stream_lookup(rows)
    opportunities = drift_symbolic_opportunities(shared_events)
    replay_by_event = {
        int(item["event_id"]): item
        for item in replay_transactions
    }
    state = initial_state
    maintenance: list[SymbolicMaintenanceRecord] = []
    publications: list[tuple[int, RuleBaseState]] = []

    for opportunity in opportunities:
        replay = replay_by_event.get(opportunity.opportunity_id)
        if replay is None:
            maintenance.append(
                SymbolicMaintenanceRecord(
                    arm="d_drift",
                    opportunity_id=opportunity.opportunity_id,
                    opportunity_clock=opportunity.logical_clock,
                    status="blocked_no_executable_neural_child",
                    neural_checkpoint_sha256=None,
                    generation_evidence_id=None,
                    generation_row_ids=(),
                    validation_row_ids=(),
                    validation_completion_clock=None,
                    symbolic_publication_effective_index=None,
                    parent_rule_base_version_id=state.rule_base_version_id,
                    result_rule_base_version_id=state.rule_base_version_id,
                    parent_rule_base_sha256=state.canonical_sha256,
                    result_rule_base_sha256=state.canonical_sha256,
                    history_sha256=state.history_sha256,
                    lifecycle=None,
                )
            )
            continue
        checkpoint_sha = str(replay["child_checkpoint_sha256"])
        effective = int(replay["publication_effective_index"])
        generation_ids = tuple(
            str(item) for item in replay["current_row_ids"]
        )
        state, record, _ = _complete_one(
            state=state,
            opportunity=opportunity,
            checkpoint_sha256=checkpoint_sha,
            checkpoint_effective_index=effective,
            generation_row_ids=generation_ids,
            rows=rows,
            lookup=lookup,
            model_resolver=model_resolver,
            checkpoint_chain=checkpoint_chain,
            feature_names=feature_names,
            seed=seed,
            raw_affine=raw_affine,
            operator_config=operator_config,
        )
        maintenance.append(record)
        if record.symbolic_publication_effective_index is not None:
            publications.append(
                (record.symbolic_publication_effective_index, state)
            )

    return SymbolicArmTrajectory(
        seed=seed,
        arm="d_drift",
        operator_config_sha256=operator_config.sha256(),
        initial_state=initial_state,
        final_state=state,
        maintenance=tuple(maintenance),
        publications=tuple(publications),
    )


def _periodic_generation_ids(
    rows: Sequence[SharedSymbolicRow],
    *,
    target_clock: int,
) -> tuple[str, ...] | None:
    eligible = [
        row
        for row in rows
        if row.origin_index <= target_clock
        and row.maturity_index <= target_clock
    ]
    eligible.sort(
        key=lambda item: (
            item.maturity_index,
            item.origin_index,
            item.row_id,
        )
    )
    if len(eligible) < 10_000:
        return None
    return tuple(row.row_id for row in eligible[-10_000:])


def run_periodic_symbolic_arm(
    *,
    seed: int,
    initial_state: RuleBaseState,
    checkpoint_chain: Sequence[Mapping[str, Any]],
    rows: Sequence[SharedSymbolicRow],
    feature_names: Sequence[str],
    model_resolver: ModelResolver,
    raw_affine: Mapping[str, tuple[float, float]] | None = None,
    operator_config: SymbolicOperatorConfig = SymbolicOperatorConfig(),
) -> SymbolicArmTrajectory:
    lookup = _stream_lookup(rows)
    state = initial_state
    maintenance: list[SymbolicMaintenanceRecord] = []
    publications: list[tuple[int, RuleBaseState]] = []
    pending_until = -1

    for opportunity in frozen_periodic_opportunities():
        if pending_until > opportunity.logical_clock:
            maintenance.append(
                SymbolicMaintenanceRecord(
                    arm="d_periodic",
                    opportunity_id=opportunity.opportunity_id,
                    opportunity_clock=opportunity.logical_clock,
                    status="pending_transaction_skip",
                    neural_checkpoint_sha256=None,
                    generation_evidence_id=None,
                    generation_row_ids=(),
                    validation_row_ids=(),
                    validation_completion_clock=pending_until,
                    symbolic_publication_effective_index=None,
                    parent_rule_base_version_id=state.rule_base_version_id,
                    result_rule_base_version_id=state.rule_base_version_id,
                    parent_rule_base_sha256=state.canonical_sha256,
                    result_rule_base_sha256=state.canonical_sha256,
                    history_sha256=state.history_sha256,
                    lifecycle=None,
                )
            )
            continue

        checkpoint = _checkpoint_at_next_prediction(
            checkpoint_chain,
            opportunity.logical_clock,
        )
        checkpoint_sha = str(checkpoint["checkpoint_file_sha256"])
        checkpoint_effective = int(
            checkpoint["publication_effective_index"]
        )
        generation_ids = _periodic_generation_ids(
            rows,
            target_clock=opportunity.logical_clock,
        )
        if generation_ids is None:
            maintenance.append(
                SymbolicMaintenanceRecord(
                    arm="d_periodic",
                    opportunity_id=opportunity.opportunity_id,
                    opportunity_clock=opportunity.logical_clock,
                    status="insufficient_generation_rows",
                    neural_checkpoint_sha256=checkpoint_sha,
                    generation_evidence_id=None,
                    generation_row_ids=(),
                    validation_row_ids=(),
                    validation_completion_clock=None,
                    symbolic_publication_effective_index=None,
                    parent_rule_base_version_id=state.rule_base_version_id,
                    result_rule_base_version_id=state.rule_base_version_id,
                    parent_rule_base_sha256=state.canonical_sha256,
                    result_rule_base_sha256=state.canonical_sha256,
                    history_sha256=state.history_sha256,
                    lifecycle=None,
                )
            )
            continue

        state, record, pending_until = _complete_one(
            state=state,
            opportunity=opportunity,
            checkpoint_sha256=checkpoint_sha,
            checkpoint_effective_index=checkpoint_effective,
            generation_row_ids=generation_ids,
            rows=rows,
            lookup=lookup,
            model_resolver=model_resolver,
            checkpoint_chain=checkpoint_chain,
            feature_names=feature_names,
            seed=seed,
            raw_affine=raw_affine,
            operator_config=operator_config,
        )
        maintenance.append(record)
        if record.symbolic_publication_effective_index is not None:
            publications.append(
                (record.symbolic_publication_effective_index, state)
            )

    return SymbolicArmTrajectory(
        seed=seed,
        arm="d_periodic",
        operator_config_sha256=operator_config.sha256(),
        initial_state=initial_state,
        final_state=state,
        maintenance=tuple(maintenance),
        publications=tuple(publications),
    )


def frozen_c_arm(
    *,
    seed: int,
    initial_state: RuleBaseState,
    operator_config: SymbolicOperatorConfig = SymbolicOperatorConfig(),
) -> SymbolicArmTrajectory:
    return SymbolicArmTrajectory(
        seed=seed,
        arm="c_frozen_symbolic",
        operator_config_sha256=operator_config.sha256(),
        initial_state=initial_state,
        final_state=initial_state,
        maintenance=(),
        publications=(),
    )


def verify_symbolic_arm_control_plane_isolation(
    trajectories: Sequence[SymbolicArmTrajectory],
    *,
    shared_identity_sha256: str,
) -> str:
    if not shared_identity_sha256:
        raise ValueError("Shared control-plane identity is required.")
    operator_hashes = {
        trajectory.operator_config_sha256
        for trajectory in trajectories
        if trajectory.arm in {"d_drift", "d_periodic"}
    }
    if len(operator_hashes) > 1:
        raise ValueError("D trigger arms use different symbolic operators.")
    return canonical_sha256(
        {
            "shared_identity_sha256": str(shared_identity_sha256),
            "arms": [
                {
                    "arm": trajectory.arm,
                    "seed": trajectory.seed,
                    "operator_config_sha256": (
                        trajectory.operator_config_sha256
                    ),
                }
                for trajectory in sorted(
                    trajectories,
                    key=lambda item: item.arm,
                )
            ],
        }
    )
