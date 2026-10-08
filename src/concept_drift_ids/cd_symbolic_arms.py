from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from concept_drift_ids.cd_control_plane import canonical_sha256
from concept_drift_ids.cd_symbolic_candidates import SymbolicGenerationConfig
from concept_drift_ids.cd_symbolic_lifecycle import (
    CandidateRule,
    LifecycleResult,
    OnlineRuleGate,
    RuleBaseState,
    apply_lifecycle_maintenance,
)


PRIMARY_STREAM_LENGTH = 138_530
PRIMARY_SYMBOLIC_VALIDATION_ROWS = 10_000
PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET = 4
PRIMARY_PERIODIC_CLOCKS = (27_706, 55_412, 83_118, 110_824)


@dataclass(frozen=True)
class SymbolicValidationRecord:
    row_id: str
    origin_index: int
    maturity_index: int
    neural_checkpoint_sha256: str
    features: np.ndarray
    true_label: int
    neural_decision: int


@dataclass(frozen=True)
class SymbolicOpportunity:
    arm: str
    opportunity_id: int
    source: str
    logical_clock: int
    shared_neural_checkpoint_sha256: str | None
    status: str = "scheduled"


@dataclass(frozen=True)
class ValidationBlockResult:
    status: str
    records: tuple[SymbolicValidationRecord, ...]

    @property
    def row_ids(self) -> tuple[str, ...]:
        return tuple(record.row_id for record in self.records)


@dataclass(frozen=True)
class SymbolicOperatorConfig:
    generation: SymbolicGenerationConfig = SymbolicGenerationConfig()
    gate: OnlineRuleGate = OnlineRuleGate()
    validation_rows: int = PRIMARY_SYMBOLIC_VALIDATION_ROWS
    same_class_redundancy: float = 0.95
    refinement_overlap: float = 0.50
    cross_class_overlap: float = 0.50

    def sha256(self) -> str:
        return canonical_sha256(
            {
                "generation": asdict(self.generation),
                "gate": asdict(self.gate),
                "validation_rows": self.validation_rows,
                "same_class_redundancy": self.same_class_redundancy,
                "refinement_overlap": self.refinement_overlap,
                "cross_class_overlap": self.cross_class_overlap,
            }
        )


@dataclass(frozen=True)
class PendingSymbolicTransaction:
    arm: str
    opportunity_id: int
    opportunity_clock: int
    neural_checkpoint_sha256: str
    checkpoint_publication_effective_index: int
    generation_row_ids: tuple[str, ...]
    generation_evidence_id: str
    candidates: tuple[CandidateRule, ...]
    operator_config_sha256: str


@dataclass(frozen=True)
class SymbolicTransactionResult:
    status: str
    opportunity_id: int
    validation_row_ids: tuple[str, ...]
    lifecycle: LifecycleResult | None


def frozen_periodic_opportunities(
    *,
    stream_length: int = PRIMARY_STREAM_LENGTH,
) -> tuple[SymbolicOpportunity, ...]:
    if stream_length != PRIMARY_STREAM_LENGTH:
        raise ValueError(
            "Primary D-periodic schedule is frozen to the 138,530-row stream."
        )
    derived = tuple(
        (index * stream_length) // 5
        for index in range(1, PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET + 1)
    )
    if derived != PRIMARY_PERIODIC_CLOCKS:
        raise AssertionError("Frozen periodic clocks do not reproduce exactly.")
    return tuple(
        SymbolicOpportunity(
            arm="d_periodic",
            opportunity_id=index,
            source="periodic",
            logical_clock=clock,
            shared_neural_checkpoint_sha256=None,
        )
        for index, clock in enumerate(PRIMARY_PERIODIC_CLOCKS, start=1)
    )


def drift_symbolic_opportunities(
    detector_events: Sequence[Mapping[str, Any]],
) -> tuple[SymbolicOpportunity, ...]:
    confirmed = [
        event
        for event in detector_events
        if event.get("event_type") == "drift_event"
        and event.get("status") == "confirmed"
    ]
    confirmed.sort(
        key=lambda event: (
            int(event["logical_clock"]),
            str(event["event_id"]),
        )
    )
    out: list[SymbolicOpportunity] = []
    for index, event in enumerate(
        confirmed[:PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET],
        start=1,
    ):
        out.append(
            SymbolicOpportunity(
                arm="d_drift",
                opportunity_id=index,
                source="drift",
                logical_clock=int(event["logical_clock"]),
                shared_neural_checkpoint_sha256=(
                    str(event["neural_checkpoint_sha256"])
                    if event.get("neural_checkpoint_sha256") is not None
                    else None
                ),
            )
        )
    return tuple(out)


def verify_trigger_operator_identity(
    drift_config_sha256: str,
    periodic_config_sha256: str,
) -> None:
    if str(drift_config_sha256) != str(periodic_config_sha256):
        raise ValueError(
            "D-drift and D-periodic symbolic operator configurations diverge."
        )


def open_symbolic_transaction(
    opportunity: SymbolicOpportunity,
    *,
    neural_checkpoint_sha256: str,
    checkpoint_publication_effective_index: int,
    generation_row_ids: Sequence[str],
    generation_evidence_id: str,
    candidates: Sequence[CandidateRule],
    operator_config: SymbolicOperatorConfig = SymbolicOperatorConfig(),
) -> PendingSymbolicTransaction:
    if not 1 <= opportunity.opportunity_id <= PRIMARY_SYMBOLIC_OPPORTUNITY_BUDGET:
        raise ValueError("Symbolic opportunity exceeds frozen four-slot budget.")
    if len(generation_row_ids) != 10_000:
        raise ValueError(
            "Primary symbolic candidate generation requires exactly 10,000 rows."
        )
    if len(set(generation_row_ids)) != len(generation_row_ids):
        raise ValueError("Generation evidence row IDs must be unique.")
    return PendingSymbolicTransaction(
        arm=opportunity.arm,
        opportunity_id=opportunity.opportunity_id,
        opportunity_clock=opportunity.logical_clock,
        neural_checkpoint_sha256=str(neural_checkpoint_sha256),
        checkpoint_publication_effective_index=int(
            checkpoint_publication_effective_index
        ),
        generation_row_ids=tuple(str(item) for item in generation_row_ids),
        generation_evidence_id=str(generation_evidence_id),
        candidates=tuple(candidates),
        operator_config_sha256=operator_config.sha256(),
    )


def collect_independent_validation_block(
    records: Sequence[SymbolicValidationRecord],
    transaction: PendingSymbolicTransaction,
    *,
    superseding_checkpoint_effective_index: int | None,
    required_rows: int = PRIMARY_SYMBOLIC_VALIDATION_ROWS,
) -> ValidationBlockResult:
    if required_rows <= 0:
        raise ValueError("required_rows must be positive.")
    generation = set(transaction.generation_row_ids)
    eligible: list[SymbolicValidationRecord] = []
    for record in sorted(
        records,
        key=lambda item: (
            item.origin_index,
            item.maturity_index,
            item.row_id,
        ),
    ):
        if record.row_id in generation:
            continue
        if (
            record.origin_index
            < transaction.checkpoint_publication_effective_index
        ):
            continue
        if (
            record.neural_checkpoint_sha256
            != transaction.neural_checkpoint_sha256
        ):
            continue
        if superseding_checkpoint_effective_index is not None:
            if record.maturity_index >= superseding_checkpoint_effective_index:
                continue
        if record.maturity_index < record.origin_index:
            raise ValueError("Validation label maturity precedes row origin.")
        eligible.append(record)
        if len(eligible) == required_rows:
            break

    if len(eligible) < required_rows:
        status = (
            "superseded_before_validation"
            if superseding_checkpoint_effective_index is not None
            else "right_censored_validation"
        )
        return ValidationBlockResult(status=status, records=tuple(eligible))

    labels = {record.true_label for record in eligible}
    if labels != {0, 1}:
        return ValidationBlockResult(
            status="insufficient_validation_class_diversity",
            records=tuple(eligible),
        )
    return ValidationBlockResult(
        status="complete",
        records=tuple(eligible),
    )


def complete_symbolic_transaction(
    state: RuleBaseState,
    transaction: PendingSymbolicTransaction,
    validation: ValidationBlockResult,
    *,
    feature_names: Sequence[str],
    validation_evidence_id: str,
    publication_effective_index: int,
    operator_config: SymbolicOperatorConfig = SymbolicOperatorConfig(),
) -> SymbolicTransactionResult:
    if transaction.operator_config_sha256 != operator_config.sha256():
        raise ValueError("Symbolic operator configuration hash mismatch.")
    if validation.status != "complete":
        return SymbolicTransactionResult(
            status=validation.status,
            opportunity_id=transaction.opportunity_id,
            validation_row_ids=validation.row_ids,
            lifecycle=None,
        )
    if len(validation.records) != operator_config.validation_rows:
        raise ValueError("Completed validation block has the wrong row count.")
    if set(transaction.generation_row_ids).intersection(validation.row_ids):
        raise ValueError(
            "Candidate-generation and symbolic-validation evidence overlap."
        )
    if any(
        record.neural_checkpoint_sha256
        != transaction.neural_checkpoint_sha256
        for record in validation.records
    ):
        raise ValueError("Symbolic validation is not checkpoint-pure.")

    X = np.stack(
        [np.asarray(record.features) for record in validation.records]
    )
    y = np.asarray(
        [record.true_label for record in validation.records],
        dtype=np.int8,
    )
    neural_decision = np.asarray(
        [record.neural_decision for record in validation.records],
        dtype=np.int8,
    )
    base = 20261020 + 1000 * state.seed + 10 * transaction.opportunity_id
    lifecycle = apply_lifecycle_maintenance(
        state,
        candidates=transaction.candidates,
        X_validation=X,
        y_validation=y,
        neural_decision=neural_decision,
        feature_names=feature_names,
        opportunity_id=transaction.opportunity_id,
        validation_evidence_id=validation_evidence_id,
        neural_checkpoint_sha256=transaction.neural_checkpoint_sha256,
        publication_effective_index=publication_effective_index,
        bootstrap_random_state=base + 3,
        gate=operator_config.gate,
        same_class_redundancy=operator_config.same_class_redundancy,
        refinement_overlap=operator_config.refinement_overlap,
        cross_class_overlap=operator_config.cross_class_overlap,
    )
    return SymbolicTransactionResult(
        status=lifecycle.maintenance_status,
        opportunity_id=transaction.opportunity_id,
        validation_row_ids=validation.row_ids,
        lifecycle=lifecycle,
    )


def verify_periodic_schedule(
    opportunities: Iterable[SymbolicOpportunity],
) -> None:
    items = tuple(opportunities)
    clocks = tuple(item.logical_clock for item in items)
    ids = tuple(item.opportunity_id for item in items)
    if clocks != PRIMARY_PERIODIC_CLOCKS:
        raise ValueError("Periodic opportunity clocks differ from frozen schedule.")
    if ids != (1, 2, 3, 4):
        raise ValueError("Periodic opportunity IDs differ from frozen budget.")
    if any(item.source != "periodic" for item in items):
        raise ValueError("Non-periodic source present in periodic schedule.")



def verify_primary_symbolic_operator_config(
    config: SymbolicOperatorConfig,
) -> None:
    if config != SymbolicOperatorConfig():
        raise ValueError(
            "Primary symbolic operator differs from the frozen configuration."
        )
    verify_periodic_schedule(frozen_periodic_opportunities())
