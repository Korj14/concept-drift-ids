"""Stage-10A-S prospective independent rule confirmation (NOT frozen).

This is a substantive Phase-B operator, not a prediction fixture. It consumes
preselected immutable candidates and sealed, fully matured shared-control
records. Neither primary R symbolic source nor its E1/E2/E3 estimands change.

An S rule cannot be called independently confirmed until an additional,
strictly future-of-selection, disjoint confirmation block has completed.
The proposed 10,000-row count and its gates still require prospective G1
scientific freeze. This module does not publish a rule base or run treatment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from concept_drift_ids.cd_control_plane import canonical_sha256
from concept_drift_ids.cd_symbolic_arms import SymbolicValidationRecord
from concept_drift_ids.cd_symbolic_lifecycle import (
    CandidateRule, OnlineRuleGate, evaluate_rule_mask,
)
from concept_drift_ids.symbolic import activation_mask

STREAM_ROWS = 138_530
LATENCY = 5_000
PROPOSED_CONFIRM_ROWS = 10_000


@dataclass(frozen=True)
class IndependentConfirmationResult:
    status: str
    row_ids: tuple[str, ...]
    candidate_evidence: tuple[dict[str, Any], ...]
    publication_effective_index: int | None
    evidence_sha256: str


def confirm_selected_candidates(
    *,
    selected: Sequence[CandidateRule],
    confirmed_selection_validation_ids: Sequence[str],
    generation_ids: Sequence[str],
    selection_completion_clock: int,
    confirmation_records: Sequence[SymbolicValidationRecord],
    checkpoint_sha256: str,
    next_checkpoint_effective_index: int | None,
    feature_names: Sequence[str],
    seed: int,
    opportunity_id: int,
    required_rows: int = PROPOSED_CONFIRM_ROWS,
    gate: OnlineRuleGate = OnlineRuleGate(),
) -> IndependentConfirmationResult:
    """Read-only S confirmation. No primary R state is mutated or published.

    The caller must independently verify that `selected` passed the original
    generation/validation decision. Confirmation alone does not establish
    that upstream selection was valid or a G1 freeze exists.
    """
    if (type(seed) is not int or seed not in range(5)
        or type(opportunity_id) is not int or not 1 <= opportunity_id <= 4
        or type(required_rows) is not int or required_rows <= 0
        or type(selection_completion_clock) is not int
        or not 0 <= selection_completion_clock < STREAM_ROWS
        or type(checkpoint_sha256) is not str or len(checkpoint_sha256) != 64
        or any(c not in "0123456789abcdef" for c in checkpoint_sha256)
        or next_checkpoint_effective_index is not None
        and (type(next_checkpoint_effective_index) is not int
             or not 0 <= next_checkpoint_effective_index <= STREAM_ROWS)):
        raise ValueError("Invalid independent confirmation authority/timing")
    s_ids = tuple(confirmed_selection_validation_ids)
    g_ids = tuple(generation_ids)
    if (not s_ids or not g_ids or len(set(s_ids)) != len(s_ids)
        or len(set(g_ids)) != len(g_ids) or set(s_ids) & set(g_ids)):
        raise ValueError("Missing, duplicate or overlapping prior evidence")
    if not selected or len({c.candidate_id for c in selected}) != len(selected):
        raise ValueError("Selected candidate identities must be present and distinct")
    if any(type(c) is not CandidateRule or c.seed != seed for c in selected):
        raise ValueError("Selected candidate seed/identity mismatch")
    if len(set(feature_names)) != len(feature_names) or not feature_names:
        raise ValueError("Feature names absent or duplicated")

    used = set(s_ids) | set(g_ids)
    seen: set[str] = set()
    eligible: list[SymbolicValidationRecord] = []
    for record in sorted(confirmation_records, key=lambda x: (x.origin_index, x.row_id)):
        if (record.row_id in seen or record.row_id in used
            or record.maturity_index != record.origin_index + LATENCY
            or not 0 <= record.origin_index < STREAM_ROWS
            or record.true_label not in (0, 1)
            or record.neural_decision not in (0, 1)):
            raise ValueError("Confirmation evidence duplicates/leaks or violates maturity")
        seen.add(record.row_id)
        # Strictly subsequent to validation COMPLETION, not merely validation
        # origin. A selection decision cannot influence its own confirmation.
        if record.origin_index <= selection_completion_clock:
            continue
        if record.maturity_index >= STREAM_ROWS:
            continue
        if record.neural_checkpoint_sha256 != checkpoint_sha256:
            continue
        if (next_checkpoint_effective_index is not None
            and record.maturity_index >= next_checkpoint_effective_index):
            continue
        eligible.append(record)
        if len(eligible) >= required_rows:
            break

    chosen = tuple(eligible)
    rows = tuple(x.row_id for x in chosen)
    metrics: list[dict[str, Any]] = []
    published = None
    if len(chosen) < required_rows:
        status = ("superseded_before_confirmation"
                  if next_checkpoint_effective_index is not None
                  else "right_censored_confirmation")
    elif {x.true_label for x in chosen} != {0, 1}:
        status = "insufficient_confirmation_class_diversity"
    else:
        X = np.stack([np.asarray(x.features, dtype=np.float32) for x in chosen])
        y = np.array([x.true_label for x in chosen], dtype=np.int8)
        neural = np.array([x.neural_decision for x in chosen], dtype=np.int8)
        for i, candidate in enumerate(sorted(selected, key=lambda c: c.candidate_id)):
            mask = activation_mask(
                X, feature_names=feature_names, conditions=candidate.conditions
            )
            evidence = evaluate_rule_mask(
                mask, y_true=y, neural_decision=neural,
                consequent=candidate.consequent,
                complexity=len(candidate.conditions), gate=gate,
                bootstrap_random_state=20261101 + 1000 * seed + 10 * opportunity_id + i,
            )
            metrics.append({
                "candidate_id": candidate.candidate_id,
                "semantic_rule_id": candidate.semantic_rule_id,
                "independently_confirmed": bool(evidence.gate_pass),
                **evidence.to_dict(),
            })
        if any(e["independently_confirmed"] for e in metrics):
            status = "independently_confirmed_subset"
            published = max(x.maturity_index for x in chosen) + 1
            if (published >= STREAM_ROWS or
                next_checkpoint_effective_index is not None
                and published >= next_checkpoint_effective_index):
                status, published = "confirmation_censored_at_publication", None
        else:
            status = "confirmation_quality_failed"

    body = {
        "status": status, "seed": seed, "opportunity_id": opportunity_id,
        "neural_checkpoint_sha256": checkpoint_sha256,
        "selection_completion_clock": selection_completion_clock,
        "prior_generation_sha256": canonical_sha256(list(g_ids)),
        "prior_validation_sha256": canonical_sha256(list(s_ids)),
        "confirmation_row_ids": list(rows),
        "candidate_evidence": metrics,
        "publication_effective_index": published,
        "S_method_prospectively_frozen": False,
    }
    return IndependentConfirmationResult(
        status, rows, tuple(metrics), published, canonical_sha256(body)
    )
