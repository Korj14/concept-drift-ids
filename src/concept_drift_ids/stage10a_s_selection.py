"""Stage-10A-S Phase-B: bind independent confirmation to *actual* validation.

This is a prospective S-only, read-only selection/confirmation path built on
the inherited symbolic lifecycle. It discards provisional R-style publication
and never updates primary R or Phase-A. The full S state machine and numerical
freeze remain OPEN; no real treatment launcher is exposed here.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence

from concept_drift_ids.cd_control_plane import canonical_sha256
from concept_drift_ids.cd_symbolic_arms import (
    PRIMARY_STREAM_LENGTH, PendingSymbolicTransaction, SymbolicOperatorConfig,
    SymbolicValidationRecord, ValidationBlockResult, complete_symbolic_transaction,
)
from concept_drift_ids.cd_symbolic_lifecycle import RuleBaseState
from concept_drift_ids.stage10a_s_confirmation import (
    IndependentConfirmationResult, confirm_selected_candidates,
)

LATENCY = 5_000


@dataclass(frozen=True)
class SSelectionConfirmation:
    selection_status: str
    validation_row_ids_sha256: str
    provisional_selection_sha256: str | None
    selected_candidate_ids: tuple[str, ...]
    confirmation: IndependentConfirmationResult | None
    # A confirmation flag is not permission to activate a rule in S.
    s_phase_b_rule_publication_authorized: bool = False


def validate_and_confirm_s_selection(
    *,
    initial_s_state: RuleBaseState,
    transaction: PendingSymbolicTransaction,
    validation: ValidationBlockResult,
    confirmation_records: Sequence[SymbolicValidationRecord],
    feature_names: Sequence[str],
    operator_config: SymbolicOperatorConfig,
    next_checkpoint_effective_index: int | None,
    required_confirmation_rows: int = 10_000,
) -> SSelectionConfirmation:
    """No arbitrary caller-selected rules: first recompute accepted selection.

    The source records must come from an independently verified, sealed
    shared Phase-A writer; this function does not authenticate them itself.
    """
    if (transaction.operator_config_sha256 != operator_config.sha256()
        or initial_s_state.seed not in range(5)
        or transaction.arm not in {"d_drift", "d_periodic"}
        or not 1 <= transaction.opportunity_id <= 4
        or any(c.seed != initial_s_state.seed or
               c.generation_evidence_id != transaction.generation_evidence_id
               for c in transaction.candidates)):
        raise ValueError("S selection identity/operator differs from frozen primary source")
    if (len(transaction.generation_row_ids) != 10_000
        or len(set(transaction.generation_row_ids)) != 10_000
        or len(set(c.candidate_id for c in transaction.candidates))
           != len(transaction.candidates)):
        raise ValueError("S generation evidence/candidates are not unique")
    prior_candidate_ids = {
        r.source_candidate_id for r in initial_s_state.revisions
        if r.source_candidate_id is not None
    }
    if prior_candidate_ids.intersection(
        c.candidate_id for c in transaction.candidates
    ):
        raise ValueError("S candidate ID collides with historical rule provenance")
    if validation.status != "complete":
        return SSelectionConfirmation(
            "selection_validation_not_complete",
            canonical_sha256(list(validation.row_ids)), None, (), None,
        )
    if len(validation.records) != operator_config.validation_rows:
        raise ValueError("Selection validation size differs from frozen operator")
    ids = tuple(r.row_id for r in validation.records)
    if (len(set(ids)) != len(ids)
        or set(ids) & set(transaction.generation_row_ids)):
        raise ValueError("S selection validation evidence overlaps generation")
    if not feature_names or len(set(feature_names)) != len(feature_names):
        raise ValueError("Missing or duplicate S feature names")
    for record in validation.records:
        if (record.origin_index < transaction.validation_start_index
            or record.maturity_index != record.origin_index + LATENCY
            or not 0 <= record.origin_index < PRIMARY_STREAM_LENGTH
            or record.maturity_index >= PRIMARY_STREAM_LENGTH
            or record.neural_checkpoint_sha256 != transaction.neural_checkpoint_sha256
            or type(record.true_label) is not int or record.true_label not in (0, 1)
            or type(record.neural_decision) is not int
            or record.neural_decision not in (0, 1)):
            raise ValueError("S selection validation timing/checkpoint mismatch")
    selection_completion = max(r.maturity_index for r in validation.records)
    publication_clock = selection_completion + 1
    if (next_checkpoint_effective_index is not None
        and publication_clock >= next_checkpoint_effective_index):
        return SSelectionConfirmation(
            "selection_checkpoint_superseded",
            canonical_sha256(list(ids)), None, (), None,
        )
    if publication_clock >= PRIMARY_STREAM_LENGTH:
        return SSelectionConfirmation(
            "selection_right_censored",
            canonical_sha256(list(ids)), None, (), None,
        )
    selection = complete_symbolic_transaction(
        initial_s_state, transaction, validation,
        feature_names=feature_names,
        validation_evidence_id=canonical_sha256({
            "arm": transaction.arm, "opportunity_id": transaction.opportunity_id,
            "status": "complete", "row_ids": list(ids),
            "neural_checkpoint_sha256": transaction.neural_checkpoint_sha256,
        }),
        publication_effective_index=publication_clock,
        operator_config=operator_config,
    )
    if selection.lifecycle is None:
        raise AssertionError("Complete validation cannot omit lifecycle evidence")

    # Selected means this candidate actually survived primary quality,
    # redundancy and conflict resolution in the provisional lifecycle,
    # not merely that it passed a standalone bootstrap quality gate.
    previously_active = {
        r.rule_revision_id for r in initial_s_state.active_revisions()
    }
    activated = {
        r.source_candidate_id
        for r in selection.lifecycle.state.active_revisions()
        if r.rule_revision_id not in previously_active
        and r.valid_from == publication_clock
        and r.source_candidate_id is not None
    }
    selected = tuple(
        c for c in transaction.candidates if c.candidate_id in activated
    )
    if not selected:
        return SSelectionConfirmation(
            "no_new_candidate_selected",
            canonical_sha256(list(ids)),
            selection.lifecycle.state.canonical_sha256, (), None,
        )

    confirm = confirm_selected_candidates(
        selected=selected,
        generation_ids=transaction.generation_row_ids,
        confirmed_selection_validation_ids=ids,
        selection_completion_clock=publication_clock,
        confirmation_records=confirmation_records,
        checkpoint_sha256=transaction.neural_checkpoint_sha256,
        next_checkpoint_effective_index=next_checkpoint_effective_index,
        feature_names=feature_names,
        seed=initial_s_state.seed,
        opportunity_id=transaction.opportunity_id,
        required_rows=required_confirmation_rows,
        gate=operator_config.gate,
    )
    return SSelectionConfirmation(
        selection_status="selected_then_confirmation_evaluated",
        validation_row_ids_sha256=canonical_sha256(list(ids)),
        provisional_selection_sha256=selection.lifecycle.state.canonical_sha256,
        selected_candidate_ids=tuple(sorted(c.candidate_id for c in selected)),
        confirmation=confirm,
    )


@dataclass(frozen=True)
class SDelayedRuleBase:
    """A candidate S rule-base *proposal*, not a scientific RELEASE."""
    selection: SSelectionConfirmation
    state: RuleBaseState | None
    valid_from: int | None
    # The S variant/thresholds still need independent scientific freeze.
    s_variant_frozen: bool = False


def derive_s_delayed_rule_base(
    *,
    initial_s_state: RuleBaseState,
    transaction: PendingSymbolicTransaction,
    validation: ValidationBlockResult,
    confirmation_records: Sequence[SymbolicValidationRecord],
    feature_names: Sequence[str],
    operator_config: SymbolicOperatorConfig,
    next_checkpoint_effective_index: int | None,
    required_confirmation_rows: int = 10_000,
) -> SDelayedRuleBase:
    """Apply inherited lifecycle to *confirmed* new candidates only, at t+1.

    The validation selection is re-derived first. The provisional validation
    state is never exposed as an S publication; candidate publication can
    occur only after the independent matured-label confirmation finishes.
    """
    selection = validate_and_confirm_s_selection(
        initial_s_state=initial_s_state, transaction=transaction,
        validation=validation, confirmation_records=confirmation_records,
        feature_names=feature_names, operator_config=operator_config,
        next_checkpoint_effective_index=next_checkpoint_effective_index,
        required_confirmation_rows=required_confirmation_rows,
    )
    confirmation = selection.confirmation
    if (confirmation is None or confirmation.publication_effective_index is None
        or confirmation.status != "independently_confirmed_subset"):
        return SDelayedRuleBase(selection, None, None)

    confirmed = {
        m["candidate_id"] for m in confirmation.candidate_evidence
        if m["independently_confirmed"] is True
    }
    if not confirmed or not confirmed <= set(selection.selected_candidate_ids):
        raise ValueError("S confirmation is not bound to validated selection")
    filtered_transaction = replace(
        transaction,
        candidates=tuple(
            c for c in transaction.candidates if c.candidate_id in confirmed
        ),
    )
    valid_from = confirmation.publication_effective_index
    if (valid_from <= max(r.maturity_index for r in validation.records)
        or next_checkpoint_effective_index is not None
        and valid_from >= next_checkpoint_effective_index):
        raise ValueError("S rule-publication time violates independent confirmation")
    result = complete_symbolic_transaction(
        initial_s_state, filtered_transaction, validation,
        feature_names=feature_names,
        validation_evidence_id=canonical_sha256({
            "arm": transaction.arm, "opportunity_id": transaction.opportunity_id,
            "status": "complete",
            "row_ids": list(validation.row_ids),
            "neural_checkpoint_sha256": transaction.neural_checkpoint_sha256,
        }),
        publication_effective_index=valid_from,
        operator_config=operator_config,
    )
    if result.lifecycle is None:
        raise ValueError("Inherited lifecycle failed after S confirmation")
    new_state = result.lifecycle.state
    # Existing R0 rules may receive replacement revisions during
    # maintenance; those are not newly proposed candidates. Preserve their
    # independent historical provenance rather than falsely rejecting them.
    original_candidate_ids = {c.candidate_id for c in transaction.candidates}
    new_candidate_ids = {
        r.source_candidate_id for r in new_state.active_revisions()
        if r.valid_from == valid_from
        and r.source_candidate_id in original_candidate_ids
    }
    if not new_candidate_ids <= confirmed:
        raise ValueError("Unconfirmed candidate would enter S rule-base")
    if not new_candidate_ids:
        return SDelayedRuleBase(selection, None, None)
    return SDelayedRuleBase(selection, new_state, valid_from)
