"""Stage-10A-S read-only Phase-B confirmation arm over sealed Phase-A evidence.

This is a genuine alternate symbolic consumer, never another neural writer.
It uses the inherited event/replay clocks and candidate-generation mechanism,
but delays S-only candidate activation until independent confirmation.
Numerical S registration, withdrawal variants and RELEASE remain unapproved.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from torch import nn

from concept_drift_ids.cd_control_plane import SYSTEM_A_MONITOR_THRESHOLDS
from concept_drift_ids.cd_symbolic_arms import (
    PRIMARY_STREAM_LENGTH, SymbolicOperatorConfig, SymbolicOpportunity,
    collect_independent_validation_block, drift_symbolic_opportunities,
    frozen_periodic_opportunities, open_symbolic_transaction,
)
from concept_drift_ids.cd_symbolic_lifecycle import RuleBaseState
from concept_drift_ids.cd_symbolic_runner import (
    SharedSymbolicRow, _checkpoint_at_next_prediction,
    _generation_result, _next_checkpoint_effective_index,
    _periodic_generation_ids, _stream_lookup, _validation_records,
    verify_shared_symbolic_rows,
)
from concept_drift_ids.stage10a_s_selection import (
    derive_s_delayed_rule_base,
)


@dataclass(frozen=True)
class SConfirmationOpportunityRecord:
    source_arm: str
    opportunity_id: int
    opportunity_clock: int
    status: str
    neural_checkpoint_sha256: str | None
    generation_evidence_id: str | None
    validation_row_ids: tuple[str, ...]
    confirmation_row_ids: tuple[str, ...]
    validated_candidate_ids: tuple[str, ...]
    independently_confirmed_candidate_ids: tuple[str, ...]
    publication_effective_index: int | None
    result_rule_base_sha256: str


@dataclass(frozen=True)
class SConfirmationArmTrajectory:
    seed: int
    source_arm: str
    shared_identity_sha256: str
    operator_config_sha256: str
    initial_state: RuleBaseState
    final_state: RuleBaseState
    opportunities: tuple[SConfirmationOpportunityRecord, ...]
    publications: tuple[tuple[int, RuleBaseState], ...]
    prospective_s_method_frozen: bool = False
    stage10a_release_authorized: bool = False

    def state_for_prediction_index(self, index: int) -> RuleBaseState:
        state = self.initial_state
        for effective, published in self.publications:
            if effective <= index:
                state = published
            else:
                break
        return state


def run_s_confirmation_arm(
    *,
    seed: int,
    source_arm: str,
    initial_state: RuleBaseState,
    shared_identity_sha256: str,
    shared_predictions: Sequence[Mapping[str, Any]],
    shared_events: Sequence[Mapping[str, Any]],
    replay_transactions: Sequence[Mapping[str, Any]],
    checkpoint_chain: Sequence[Mapping[str, Any]],
    rows: Sequence[SharedSymbolicRow],
    feature_names: Sequence[str],
    model_resolver: Callable[[str], nn.Module],
    raw_affine: Mapping[str, tuple[float, float]] | None = None,
    operator_config: SymbolicOperatorConfig = SymbolicOperatorConfig(),
    required_confirmation_rows: int = 10_000,
) -> SConfirmationArmTrajectory:
    """Prospective S-only operator using a single already-sealed shared writer.

    No source checkpoint load occurs until a real opportunity needs candidate
    generation. Caller must independently verify Phase-A seal, checkpoint
    custody and authorized run scope before invoking on real evidence.
    """
    if (seed not in range(5) or initial_state.seed != seed
        or source_arm not in {"d_drift", "d_periodic"}
        or not shared_identity_sha256 or len(set(feature_names)) != len(feature_names)):
        raise ValueError("S Phase-B seed/arm/shared identity/feature contract invalid")
    verify_shared_symbolic_rows(rows, shared_predictions)
    lookup = _stream_lookup(rows)
    records = _validation_records(
        rows, neural_threshold=SYSTEM_A_MONITOR_THRESHOLDS[seed]
    )
    opportunities = (
        drift_symbolic_opportunities(shared_events)
        if source_arm == "d_drift" else frozen_periodic_opportunities()
    )
    replay_by_event = {
        int(item["event_id"]): item for item in replay_transactions
    }
    if len(replay_by_event) != len(replay_transactions):
        raise ValueError("Duplicate neural replay transaction identifier")

    state = initial_state
    pending_until = -1
    history: list[SConfirmationOpportunityRecord] = []
    publications: list[tuple[int, RuleBaseState]] = []

    def record(
        opportunity: SymbolicOpportunity, status: str,
        checkpoint: str | None = None, generation_id: str | None = None,
        validation_ids: tuple[str, ...] = (),
        confirmation_ids: tuple[str, ...] = (),
        selected_ids: tuple[str, ...] = (),
        confirmed_ids: tuple[str, ...] = (),
        effective: int | None = None,
    ) -> None:
        history.append(SConfirmationOpportunityRecord(
            source_arm=source_arm,
            opportunity_id=opportunity.opportunity_id,
            opportunity_clock=opportunity.logical_clock,
            status=status,
            neural_checkpoint_sha256=checkpoint,
            generation_evidence_id=generation_id,
            validation_row_ids=validation_ids,
            confirmation_row_ids=confirmation_ids,
            validated_candidate_ids=selected_ids,
            independently_confirmed_candidate_ids=confirmed_ids,
            publication_effective_index=effective,
            result_rule_base_sha256=state.canonical_sha256,
        ))

    for opportunity in opportunities:
        # No overlapping future-evidence transactions. Every planned slot
        # remains visible as an explicit skipped/invalid opportunity.
        if pending_until > opportunity.logical_clock:
            record(opportunity, "pending_confirmation_skip")
            continue
        if source_arm == "d_drift":
            replay = replay_by_event.get(opportunity.opportunity_id)
            if replay is None:
                record(opportunity, "blocked_no_neural_child")
                continue
            checkpoint_sha = str(replay["child_checkpoint_sha256"])
            checkpoint_effective = int(replay["publication_effective_index"])
            generation_ids = tuple(str(x) for x in replay["current_row_ids"])
        else:
            checkpoint = _checkpoint_at_next_prediction(
                checkpoint_chain, opportunity.logical_clock
            )
            checkpoint_sha = str(checkpoint["checkpoint_file_sha256"])
            checkpoint_effective = int(checkpoint["publication_effective_index"])
            generation_ids = _periodic_generation_ids(
                rows, target_clock=opportunity.logical_clock
            )
            if generation_ids is None:
                record(opportunity, "insufficient_generation_rows", checkpoint_sha)
                continue
        supersession = _next_checkpoint_effective_index(
            checkpoint_chain, checkpoint_sha
        )
        candidate_model = model_resolver(checkpoint_sha)
        candidates, generation_id, generation_status, _, _ = _generation_result(
            model=candidate_model, row_ids=generation_ids, lookup=lookup,
            feature_names=feature_names, seed=seed,
            opportunity_id=opportunity.opportunity_id,
            raw_affine=raw_affine, operator_config=operator_config,
        )
        txn = open_symbolic_transaction(
            opportunity,
            neural_checkpoint_sha256=checkpoint_sha,
            checkpoint_publication_effective_index=checkpoint_effective,
            generation_row_ids=generation_ids,
            generation_evidence_id=generation_id,
            candidates=candidates,
            validation_start_index=(
                opportunity.logical_clock + 1
                if source_arm == "d_periodic" else checkpoint_effective
            ),
            operator_config=operator_config,
        )
        validation = collect_independent_validation_block(
            records, txn, superseding_checkpoint_effective_index=supersession,
            required_rows=operator_config.validation_rows,
        )
        if validation.status != "complete":
            record(opportunity, validation.status + ";" + generation_status,
                   checkpoint_sha, generation_id, validation.row_ids)
            pending_until = (
                PRIMARY_STREAM_LENGTH if validation.status == "right_censored_validation"
                else max((x.maturity_index for x in validation.records), default=opportunity.logical_clock)
            )
            continue
        result = derive_s_delayed_rule_base(
            initial_s_state=state, transaction=txn, validation=validation,
            confirmation_records=records, feature_names=feature_names,
            operator_config=operator_config,
            next_checkpoint_effective_index=supersession,
            required_confirmation_rows=required_confirmation_rows,
        )
        conf = result.selection.confirmation
        confirmation_ids = conf.row_ids if conf is not None else ()
        selected_ids = result.selection.selected_candidate_ids
        confirmed_ids = (
            tuple(sorted(e["candidate_id"] for e in conf.candidate_evidence
                         if e["independently_confirmed"] is True))
            if conf is not None else ()
        )
        status = conf.status if conf is not None else result.selection.selection_status
        if result.state is not None and result.valid_from is not None:
            if publications and result.valid_from <= publications[-1][0]:
                raise ValueError("S rule-base publication order is not monotonic")
            state = result.state
            publications.append((result.valid_from, state))
            pending_until = result.valid_from
        else:
            pending_until = (
                PRIMARY_STREAM_LENGTH
                if conf is not None and conf.status.startswith("right_censored")
                else max(
                    [x.maturity_index for x in validation.records] +
                    [x.maturity_index for x in records
                     if x.row_id in set(confirmation_ids)],
                    default=opportunity.logical_clock,
                )
            )
        record(opportunity, status, checkpoint_sha, generation_id,
               validation.row_ids, confirmation_ids, selected_ids,
               confirmed_ids, result.valid_from)
    return SConfirmationArmTrajectory(
        seed=seed, source_arm=source_arm,
        shared_identity_sha256=shared_identity_sha256,
        operator_config_sha256=operator_config.sha256(),
        initial_state=initial_state, final_state=state,
        opportunities=tuple(history), publications=tuple(publications),
    )
