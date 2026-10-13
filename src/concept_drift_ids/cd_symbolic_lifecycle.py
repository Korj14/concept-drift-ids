from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from concept_drift_ids.cd_control_plane import canonical_sha256
from concept_drift_ids.symbolic import (
    Condition,
    Rule,
    activation_mask,
    overlap_statistics,
    pareto_dominates,
    stratified_bootstrap_indices,
)


WILSON_Z_ONE_SIDED_95 = 1.6448536269514722


@dataclass(frozen=True)
class OnlineRuleGate:
    min_support: float = 0.001
    min_covered: int = 25
    min_class_precision: float = 0.80
    min_precision_lcb: float = 0.80
    min_neural_fidelity: float = 0.90
    min_fidelity_lcb: float = 0.90
    min_stability: float = 0.90
    max_complexity: int = 4
    bootstrap_replicates: int = 100
    wilson_z: float = WILSON_Z_ONE_SIDED_95


@dataclass(frozen=True)
class RuleEvidence:
    support: float
    covered_count: int
    class_precision: float
    class_precision_lcb: float
    neural_fidelity: float
    neural_fidelity_lcb: float
    stability: float
    complexity: int
    gate_pass: bool
    staleness_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateRule:
    candidate_id: str
    seed: int
    conditions: tuple[Condition, ...]
    consequent: int
    generation_evidence_id: str

    @property
    def semantic_rule_id(self) -> str:
        return semantic_rule_id(
            seed=self.seed,
            conditions=self.conditions,
            consequent=self.consequent,
        )


@dataclass(frozen=True)
class RuleRevision:
    semantic_rule_id: str
    rule_revision_id: str
    lineage_id: str
    parent_rule_revision_ids: tuple[str, ...]
    parent_lineage_ids: tuple[str, ...]
    rule_base_version_id: str
    seed: int
    conditions: tuple[Condition, ...]
    consequent: int
    confidence: float
    support: float
    covered_count: int
    class_precision: float
    class_precision_lcb: float | None
    neural_fidelity: float
    neural_fidelity_lcb: float | None
    stability: float
    complexity: int
    lifecycle_state: str
    lifecycle_transition: str
    failure_streak: int
    source_candidate_id: str | None
    generation_evidence_id: str | None
    validation_evidence_id: str
    neural_checkpoint_sha256: str
    valid_from: int
    valid_to: int | None
    relations: tuple[dict[str, Any], ...] = ()

    def to_rule(self) -> Rule:
        return Rule(
            rule_id=self.semantic_rule_id,
            lineage_id=self.lineage_id,
            rule_base_version=self.rule_base_version_id,
            seed=self.seed,
            conditions=self.conditions,
            consequent=self.consequent,
            confidence=self.confidence,
            support=self.support,
            covered_count=self.covered_count,
            class_precision=self.class_precision,
            neural_fidelity=self.neural_fidelity,
            stability=self.stability,
            complexity=self.complexity,
            lifecycle_state=self.lifecycle_state,
            source_candidate_id=self.source_candidate_id or "historical",
            validation_evidence_id=self.validation_evidence_id,
            relations=tuple(self.relations),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "conditions": [condition.to_dict() for condition in self.conditions],
        }


@dataclass(frozen=True)
class RuleBaseState:
    seed: int
    rule_base_version_id: str
    version_number: int
    parent_version_id: str | None
    parent_version_sha256: str | None
    revisions: tuple[RuleRevision, ...]
    active_revision_ids: tuple[str, ...]
    canonical_sha256: str
    history_sha256: str

    def latest_by_semantic(self) -> dict[str, RuleRevision]:
        latest: dict[str, RuleRevision] = {}
        for revision in self.revisions:
            latest[revision.semantic_rule_id] = revision
        return latest

    def active_revisions(self) -> tuple[RuleRevision, ...]:
        lookup = {revision.rule_revision_id: revision for revision in self.revisions}
        return tuple(lookup[item] for item in self.active_revision_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "rule_base_version_id": self.rule_base_version_id,
            "version_number": self.version_number,
            "parent_version_id": self.parent_version_id,
            "parent_version_sha256": self.parent_version_sha256,
            "active_revision_ids": list(self.active_revision_ids),
            "revisions": [revision.to_dict() for revision in self.revisions],
            "canonical_sha256": self.canonical_sha256,
            "history_sha256": self.history_sha256,
        }


@dataclass(frozen=True)
class LifecycleResult:
    state: RuleBaseState
    published: bool
    maintenance_status: str
    decisions: tuple[dict[str, Any], ...]
    staleness_snapshot: tuple[dict[str, Any], ...]
    candidate_evidence: tuple[dict[str, Any], ...]


def _condition_payload(conditions: Sequence[Condition]) -> list[dict[str, Any]]:
    return [
        {
            "feature": condition.feature,
            "operator": condition.operator,
            "threshold": float(condition.threshold),
        }
        for condition in conditions
    ]


def _active_payload_hash(
    *,
    seed: int,
    rule_base_version_id: str,
    active_revisions: Sequence[RuleRevision],
) -> str:
    payload = {
        "seed": int(seed),
        "rule_base_version_id": str(rule_base_version_id),
        "active_rules": [
            {
                "semantic_rule_id": revision.semantic_rule_id,
                "lineage_id": revision.lineage_id,
                "antecedent": _condition_payload(revision.conditions),
                "consequent": int(revision.consequent),
                "confidence": float(revision.confidence),
                "relations": list(revision.relations),
            }
            for revision in sorted(
                active_revisions,
                key=lambda item: item.semantic_rule_id,
            )
        ],
    }
    return canonical_sha256(payload)


def _history_hash(revisions: Sequence[RuleRevision]) -> str:
    return canonical_sha256(
        [
            revision.to_dict()
            for revision in sorted(
                revisions,
                key=lambda item: (
                    item.valid_from,
                    item.semantic_rule_id,
                    item.rule_revision_id,
                ),
            )
        ]
    )


def semantic_rule_id(
    *,
    seed: int,
    conditions: Sequence[Condition],
    consequent: int,
) -> str:
    payload = {
        "seed": int(seed),
        "antecedent": _condition_payload(conditions),
        "consequent": int(consequent),
    }
    return f"sem-s{seed}-{canonical_sha256(payload)[:16]}"


def rule_revision_id(
    *,
    semantic_id: str,
    opportunity_id: int,
    transition: str,
    evidence_id: str,
    ordinal: int,
) -> str:
    payload = {
        "semantic_rule_id": semantic_id,
        "opportunity_id": int(opportunity_id),
        "transition": str(transition),
        "validation_evidence_id": str(evidence_id),
        "ordinal": int(ordinal),
    }
    return f"{semantic_id}-rev-{canonical_sha256(payload)[:16]}"


def wilson_lower_bound(
    successes: int,
    trials: int,
    *,
    z: float = WILSON_Z_ONE_SIDED_95,
) -> float:
    if trials <= 0:
        return 0.0
    if successes < 0 or successes > trials:
        raise ValueError("successes must lie within [0, trials].")
    p_hat = successes / trials
    z2 = z * z
    numerator = (
        p_hat
        + z2 / (2.0 * trials)
        - z
        * math.sqrt(
            p_hat * (1.0 - p_hat) / trials
            + z2 / (4.0 * trials * trials)
        )
    )
    denominator = 1.0 + z2 / trials
    return float(numerator / denominator)


def _point_gate(
    *,
    support: float,
    covered_count: int,
    precision: float,
    precision_lcb: float,
    fidelity: float,
    fidelity_lcb: float,
    complexity: int,
    gate: OnlineRuleGate,
    include_complexity: bool = True,
) -> bool:
    return bool(
        support >= gate.min_support
        and covered_count >= gate.min_covered
        and precision >= gate.min_class_precision
        and precision_lcb >= gate.min_precision_lcb
        and fidelity >= gate.min_neural_fidelity
        and fidelity_lcb >= gate.min_fidelity_lcb
        and (
            not include_complexity
            or complexity <= gate.max_complexity
        )
    )


def evaluate_rule_mask(
    mask: np.ndarray,
    *,
    y_true: np.ndarray,
    neural_decision: np.ndarray,
    consequent: int,
    complexity: int,
    gate: OnlineRuleGate,
    bootstrap_random_state: int,
) -> RuleEvidence:
    mask = np.asarray(mask, dtype=bool)
    y_true = np.asarray(y_true, dtype=np.int8)
    neural_decision = np.asarray(neural_decision, dtype=np.int8)
    if not (len(mask) == len(y_true) == len(neural_decision)):
        raise ValueError("Validation arrays have mismatched lengths.")
    if len(y_true) == 0:
        raise ValueError("Validation block must not be empty.")
    if set(np.unique(y_true)) != {0, 1}:
        raise ValueError("Both binary classes are required for validation.")

    covered = int(mask.sum())
    support = covered / len(mask)
    precision_success = int(np.sum(y_true[mask] == consequent)) if covered else 0
    fidelity_success = (
        int(np.sum(neural_decision[mask] == consequent)) if covered else 0
    )
    precision = precision_success / covered if covered else 0.0
    fidelity = fidelity_success / covered if covered else 0.0
    precision_lcb = wilson_lower_bound(
        precision_success,
        covered,
        z=gate.wilson_z,
    )
    fidelity_lcb = wilson_lower_bound(
        fidelity_success,
        covered,
        z=gate.wilson_z,
    )

    bootstrap = stratified_bootstrap_indices(
        y_true,
        replicates=gate.bootstrap_replicates,
        random_state=bootstrap_random_state,
    )
    passes = 0
    for indices in bootstrap:
        sampled_mask = mask[indices]
        sampled_y = y_true[indices]
        sampled_neural = neural_decision[indices]
        sampled_covered = int(sampled_mask.sum())
        sampled_support = sampled_covered / len(indices)
        precision_success = (
            int(np.sum(sampled_y[sampled_mask] == consequent))
            if sampled_covered
            else 0
        )
        fidelity_success = (
            int(np.sum(sampled_neural[sampled_mask] == consequent))
            if sampled_covered
            else 0
        )
        sampled_precision = (
            precision_success / sampled_covered if sampled_covered else 0.0
        )
        sampled_fidelity = (
            fidelity_success / sampled_covered if sampled_covered else 0.0
        )
        passes += int(
            _point_gate(
                support=sampled_support,
                covered_count=sampled_covered,
                precision=sampled_precision,
                precision_lcb=wilson_lower_bound(
                    precision_success,
                    sampled_covered,
                    z=gate.wilson_z,
                ),
                fidelity=sampled_fidelity,
                fidelity_lcb=wilson_lower_bound(
                    fidelity_success,
                    sampled_covered,
                    z=gate.wilson_z,
                ),
                complexity=complexity,
                gate=gate,
                include_complexity=False,
            )
        )
    stability = passes / gate.bootstrap_replicates

    point_pass = _point_gate(
        support=support,
        covered_count=covered,
        precision=precision,
        precision_lcb=precision_lcb,
        fidelity=fidelity,
        fidelity_lcb=fidelity_lcb,
        complexity=complexity,
        gate=gate,
    )
    gate_pass = bool(point_pass and stability >= gate.min_stability)

    if support < gate.min_support or covered < gate.min_covered:
        status = "evidence_insufficient"
    elif gate_pass:
        status = "valid"
    else:
        status = "quality_failed"

    return RuleEvidence(
        support=float(support),
        covered_count=covered,
        class_precision=float(precision),
        class_precision_lcb=float(precision_lcb),
        neural_fidelity=float(fidelity),
        neural_fidelity_lcb=float(fidelity_lcb),
        stability=float(stability),
        complexity=int(complexity),
        gate_pass=gate_pass,
        staleness_status=status,
    )


def migrate_r0_v2_rules(
    *,
    seed: int,
    rules: Sequence[Rule],
    neural_checkpoint_sha256: str,
    valid_from: int = 0,
) -> RuleBaseState:
    revisions: list[RuleRevision] = []
    for ordinal, rule in enumerate(sorted(rules, key=lambda item: item.rule_id)):
        if int(rule.seed) != int(seed):
            raise ValueError("R0.v2 seed mismatch during migration.")
        semantic_id = semantic_rule_id(
            seed=seed,
            conditions=rule.conditions,
            consequent=rule.consequent,
        )
        revision_id = rule_revision_id(
            semantic_id=semantic_id,
            opportunity_id=0,
            transition="migrated_r0_v2",
            evidence_id=rule.validation_evidence_id,
            ordinal=ordinal,
        )
        revisions.append(
            RuleRevision(
                semantic_rule_id=semantic_id,
                rule_revision_id=revision_id,
                lineage_id=rule.lineage_id,
                parent_rule_revision_ids=(),
                parent_lineage_ids=(),
                rule_base_version_id=f"d-s{seed}-r0v2",
                seed=seed,
                conditions=tuple(rule.conditions),
                consequent=int(rule.consequent),
                confidence=float(rule.confidence),
                support=float(rule.support),
                covered_count=int(rule.covered_count),
                class_precision=float(rule.class_precision),
                class_precision_lcb=None,
                neural_fidelity=float(rule.neural_fidelity),
                neural_fidelity_lcb=None,
                stability=float(rule.stability),
                complexity=int(rule.complexity),
                lifecycle_state="active",
                lifecycle_transition="migrated_r0_v2",
                failure_streak=0,
                source_candidate_id=rule.source_candidate_id,
                generation_evidence_id=None,
                validation_evidence_id=rule.validation_evidence_id,
                neural_checkpoint_sha256=str(neural_checkpoint_sha256),
                valid_from=int(valid_from),
                valid_to=None,
                relations=tuple(rule.relations),
            )
        )
    version_id = f"d-s{seed}-r0v2"
    active = tuple(revisions)
    return RuleBaseState(
        seed=seed,
        rule_base_version_id=version_id,
        version_number=0,
        parent_version_id=None,
        parent_version_sha256=None,
        revisions=tuple(revisions),
        active_revision_ids=tuple(item.rule_revision_id for item in revisions),
        canonical_sha256=_active_payload_hash(
            seed=seed,
            rule_base_version_id=version_id,
            active_revisions=active,
        ),
        history_sha256=_history_hash(revisions),
    )


def _revision_from_evidence(
    base: RuleRevision | None,
    *,
    candidate: CandidateRule | None,
    evidence: RuleEvidence,
    state: str,
    transition: str,
    failure_streak: int,
    rule_base_version_id: str,
    opportunity_id: int,
    validation_evidence_id: str,
    neural_checkpoint_sha256: str,
    valid_from: int,
    ordinal: int,
    lineage_id: str,
    parent_revision_ids: Sequence[str],
    parent_lineage_ids: Sequence[str],
) -> RuleRevision:
    if base is None and candidate is None:
        raise ValueError("A base revision or candidate is required.")
    conditions = (
        tuple(candidate.conditions)
        if candidate is not None
        else tuple(base.conditions)
    )
    consequent = (
        int(candidate.consequent)
        if candidate is not None
        else int(base.consequent)
    )
    seed = int(candidate.seed) if candidate is not None else int(base.seed)
    semantic_id = semantic_rule_id(
        seed=seed,
        conditions=conditions,
        consequent=consequent,
    )
    confidence = min(
        float(evidence.class_precision),
        float(evidence.neural_fidelity),
    )
    revision_id = rule_revision_id(
        semantic_id=semantic_id,
        opportunity_id=opportunity_id,
        transition=transition,
        evidence_id=validation_evidence_id,
        ordinal=ordinal,
    )
    return RuleRevision(
        semantic_rule_id=semantic_id,
        rule_revision_id=revision_id,
        lineage_id=str(lineage_id),
        parent_rule_revision_ids=tuple(parent_revision_ids),
        parent_lineage_ids=tuple(parent_lineage_ids),
        rule_base_version_id=rule_base_version_id,
        seed=seed,
        conditions=conditions,
        consequent=consequent,
        confidence=confidence,
        support=float(evidence.support),
        covered_count=int(evidence.covered_count),
        class_precision=float(evidence.class_precision),
        class_precision_lcb=float(evidence.class_precision_lcb),
        neural_fidelity=float(evidence.neural_fidelity),
        neural_fidelity_lcb=float(evidence.neural_fidelity_lcb),
        stability=float(evidence.stability),
        complexity=int(evidence.complexity),
        lifecycle_state=str(state),
        lifecycle_transition=str(transition),
        failure_streak=int(failure_streak),
        source_candidate_id=(
            candidate.candidate_id
            if candidate is not None
            else base.source_candidate_id
        ),
        generation_evidence_id=(
            candidate.generation_evidence_id
            if candidate is not None
            else base.generation_evidence_id
        ),
        validation_evidence_id=str(validation_evidence_id),
        neural_checkpoint_sha256=str(neural_checkpoint_sha256),
        valid_from=int(valid_from),
        valid_to=None,
        relations=(),
    )


def _active_rule_object(revision: RuleRevision) -> Rule:
    return revision.to_rule()


def _same_class_winner(
    left: RuleRevision,
    right: RuleRevision,
) -> RuleRevision:
    return sorted(
        (left, right),
        key=lambda revision: (
            -revision.confidence,
            -revision.support,
            revision.complexity,
            revision.semantic_rule_id,
        ),
    )[0]


def _pareto_revision_dominates(
    left: RuleRevision,
    right: RuleRevision,
) -> bool:
    return pareto_dominates(_active_rule_object(left), _active_rule_object(right))


def apply_lifecycle_maintenance(
    state: RuleBaseState,
    *,
    candidates: Sequence[CandidateRule],
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    neural_decision: np.ndarray,
    feature_names: Sequence[str],
    opportunity_id: int,
    validation_evidence_id: str,
    neural_checkpoint_sha256: str,
    publication_effective_index: int,
    bootstrap_random_state: int,
    gate: OnlineRuleGate = OnlineRuleGate(),
    same_class_redundancy: float = 0.95,
    refinement_overlap: float = 0.50,
    cross_class_overlap: float = 0.50,
) -> LifecycleResult:
    if state.seed < 0:
        raise ValueError("Invalid state seed.")
    X_validation = np.asarray(X_validation)
    y_validation = np.asarray(y_validation, dtype=np.int8)
    neural_decision = np.asarray(neural_decision, dtype=np.int8)
    if len(X_validation) != len(y_validation):
        raise ValueError("Validation feature/label size mismatch.")
    if len(y_validation) != len(neural_decision):
        raise ValueError("Validation neural-decision size mismatch.")
    if set(np.unique(y_validation)) != {0, 1}:
        return LifecycleResult(
            state=state,
            published=False,
            maintenance_status="insufficient_validation_class_diversity",
            decisions=(),
            staleness_snapshot=(),
            candidate_evidence=(),
        )

    target_version_number = state.version_number + 1
    target_version_id = f"d-s{state.seed}-v{target_version_number:04d}"
    history_by_id = {
        revision.rule_revision_id: revision
        for revision in state.revisions
    }
    latest = state.latest_by_semantic()
    current_active = {
        revision.semantic_rule_id: revision
        for revision in state.active_revisions()
    }
    masks: dict[str, np.ndarray] = {}
    evidence_by_semantic: dict[str, RuleEvidence] = {}
    staleness: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    new_latest: dict[str, RuleRevision] = dict(latest)
    ordinal = 0

    eligible_existing = [
        revision
        for revision in latest.values()
        if revision.lifecycle_state in {"active", "demoted", "retired"}
    ]
    for revision in sorted(
        eligible_existing,
        key=lambda item: item.semantic_rule_id,
    ):
        mask = activation_mask(
            X_validation,
            feature_names=feature_names,
            conditions=revision.conditions,
        )
        masks[revision.semantic_rule_id] = mask
        evidence = evaluate_rule_mask(
            mask,
            y_true=y_validation,
            neural_decision=neural_decision,
            consequent=revision.consequent,
            complexity=revision.complexity,
            gate=gate,
            bootstrap_random_state=bootstrap_random_state,
        )
        evidence_by_semantic[revision.semantic_rule_id] = evidence
        if revision.lifecycle_state == "active":
            staleness.append(
                {
                    "semantic_rule_id": revision.semantic_rule_id,
                    "rule_revision_id": revision.rule_revision_id,
                    "status": evidence.staleness_status,
                    **evidence.to_dict(),
                }
            )

        if evidence.gate_pass:
            transition = (
                "retained"
                if revision.lifecycle_state == "active"
                else "reactivated"
            )
            next_state = "active"
            streak = 0
        else:
            if revision.lifecycle_state == "active":
                transition = "demoted"
                next_state = "demoted"
                streak = 1
            elif revision.lifecycle_state == "demoted":
                transition = "retired"
                next_state = "retired"
                streak = revision.failure_streak + 1
            else:
                transition = "retired_failed"
                next_state = "retired"
                streak = revision.failure_streak + 1

        next_revision = _revision_from_evidence(
            revision,
            candidate=None,
            evidence=evidence,
            state=next_state,
            transition=transition,
            failure_streak=streak,
            rule_base_version_id=target_version_id,
            opportunity_id=opportunity_id,
            validation_evidence_id=validation_evidence_id,
            neural_checkpoint_sha256=neural_checkpoint_sha256,
            valid_from=publication_effective_index,
            ordinal=ordinal,
            lineage_id=revision.lineage_id,
            parent_revision_ids=(revision.rule_revision_id,),
            parent_lineage_ids=(revision.lineage_id,),
        )
        ordinal += 1
        history_by_id[revision.rule_revision_id] = replace(
            revision,
            valid_to=publication_effective_index,
        )
        new_latest[revision.semantic_rule_id] = next_revision
        history_by_id[next_revision.rule_revision_id] = next_revision
        decisions.append(
            {
                "type": transition,
                "semantic_rule_id": revision.semantic_rule_id,
                "from_state": revision.lifecycle_state,
                "to_state": next_state,
            }
        )

    candidate_evidence: list[dict[str, Any]] = []
    accepted_candidates: list[
        tuple[CandidateRule, RuleEvidence, np.ndarray]
    ] = []
    for candidate in sorted(candidates, key=lambda item: item.semantic_rule_id):
        if candidate.seed != state.seed:
            raise ValueError("Candidate seed differs from rule-base seed.")
        mask = activation_mask(
            X_validation,
            feature_names=feature_names,
            conditions=candidate.conditions,
        )
        evidence = evaluate_rule_mask(
            mask,
            y_true=y_validation,
            neural_decision=neural_decision,
            consequent=candidate.consequent,
            complexity=len(candidate.conditions),
            gate=gate,
            bootstrap_random_state=bootstrap_random_state,
        )
        candidate_evidence.append(
            {
                "candidate_id": candidate.candidate_id,
                "semantic_rule_id": candidate.semantic_rule_id,
                **evidence.to_dict(),
            }
        )
        if evidence.gate_pass:
            accepted_candidates.append((candidate, evidence, mask))
        else:
            decisions.append(
                {
                    "type": "candidate_rejected_quality_gate",
                    "candidate_id": candidate.candidate_id,
                    "semantic_rule_id": candidate.semantic_rule_id,
                    "reason": evidence.staleness_status,
                }
            )

    def active_latest() -> dict[str, RuleRevision]:
        return {
            semantic: revision
            for semantic, revision in new_latest.items()
            if revision.lifecycle_state == "active"
        }

    for candidate, evidence, candidate_mask in accepted_candidates:
        semantic = candidate.semantic_rule_id
        existing = new_latest.get(semantic)
        if existing is not None:
            if existing.lifecycle_state == "active":
                decisions.append(
                    {
                        "type": "existing_semantic_identity",
                        "candidate_id": candidate.candidate_id,
                        "semantic_rule_id": semantic,
                    }
                )
                continue
            lineage = existing.lineage_id
            revision = _revision_from_evidence(
                existing,
                candidate=candidate,
                evidence=evidence,
                state="active",
                transition="reactivated",
                failure_streak=0,
                rule_base_version_id=target_version_id,
                opportunity_id=opportunity_id,
                validation_evidence_id=validation_evidence_id,
                neural_checkpoint_sha256=neural_checkpoint_sha256,
                valid_from=publication_effective_index,
                ordinal=ordinal,
                lineage_id=lineage,
                parent_revision_ids=(existing.rule_revision_id,),
                parent_lineage_ids=(existing.lineage_id,),
            )
            ordinal += 1
            history_by_id[existing.rule_revision_id] = replace(
                existing,
                valid_to=publication_effective_index,
            )
            new_latest[semantic] = revision
            history_by_id[revision.rule_revision_id] = revision
            masks[semantic] = candidate_mask
            decisions.append(
                {
                    "type": "reactivated",
                    "candidate_id": candidate.candidate_id,
                    "semantic_rule_id": semantic,
                }
            )
            continue

        prototype = _revision_from_evidence(
            None,
            candidate=candidate,
            evidence=evidence,
            state="active",
            transition="candidate_prototype",
            failure_streak=0,
            rule_base_version_id=target_version_id,
            opportunity_id=opportunity_id,
            validation_evidence_id=validation_evidence_id,
            neural_checkpoint_sha256=neural_checkpoint_sha256,
            valid_from=publication_effective_index,
            ordinal=ordinal,
            lineage_id=semantic,
            parent_revision_ids=(),
            parent_lineage_ids=(),
        )

        active_same_class: list[tuple[float, RuleRevision]] = []
        for active in active_latest().values():
            if active.consequent != candidate.consequent:
                continue
            active_mask = masks.get(active.semantic_rule_id)
            if active_mask is None:
                active_mask = activation_mask(
                    X_validation,
                    feature_names=feature_names,
                    conditions=active.conditions,
                )
                masks[active.semantic_rule_id] = active_mask
            overlap = float(
                overlap_statistics(candidate_mask, active_mask)[
                    "overlap_coefficient"
                ]
            )
            active_same_class.append((overlap, active))

        stale_same_class: list[tuple[float, RuleRevision]] = []
        for semantic_id, before in current_active.items():
            if before.consequent != candidate.consequent:
                continue
            after = new_latest.get(semantic_id)
            if after is None or after.lifecycle_state == "active":
                continue
            stale_mask = masks.get(semantic_id)
            if stale_mask is None:
                stale_mask = activation_mask(
                    X_validation,
                    feature_names=feature_names,
                    conditions=after.conditions,
                )
                masks[semantic_id] = stale_mask
            overlap = float(
                overlap_statistics(candidate_mask, stale_mask)[
                    "overlap_coefficient"
                ]
            )
            if overlap >= refinement_overlap:
                stale_same_class.append((overlap, after))

        redundant = [
            (overlap, active)
            for overlap, active in active_same_class
            if overlap >= same_class_redundancy
        ]
        if redundant:
            incumbent = sorted(
                redundant,
                key=lambda pair: (
                    -pair[0],
                    pair[1].semantic_rule_id,
                ),
            )[0][1]
            winner = _same_class_winner(prototype, incumbent)
            if winner.semantic_rule_id == incumbent.semantic_rule_id:
                decisions.append(
                    {
                        "type": "candidate_rejected_redundant",
                        "candidate_id": candidate.candidate_id,
                        "winner": incumbent.semantic_rule_id,
                    }
                )
                continue
            merged = replace(
                new_latest[incumbent.semantic_rule_id],
                lifecycle_state="merged",
                lifecycle_transition="merge_consolidation",
                valid_to=publication_effective_index,
            )
            new_latest[incumbent.semantic_rule_id] = merged
            history_by_id[incumbent.rule_revision_id] = merged
            prototype = replace(
                prototype,
                lifecycle_transition="merge_consolidation",
                parent_rule_revision_ids=(incumbent.rule_revision_id,),
                parent_lineage_ids=(incumbent.lineage_id,),
            )
            decisions.append(
                {
                    "type": "merge_consolidation",
                    "winner": semantic,
                    "merged": incumbent.semantic_rule_id,
                }
            )
        else:
            refinements = [
                (overlap, active)
                for overlap, active in active_same_class
                if refinement_overlap <= overlap < same_class_redundancy
            ]
            refinements.extend(stale_same_class)
            if refinements:
                overlap, incumbent = sorted(
                    refinements,
                    key=lambda pair: (
                        -pair[0],
                        pair[1].semantic_rule_id,
                    ),
                )[0]
                stale = incumbent.lifecycle_state != "active"
                if not (
                    _pareto_revision_dominates(prototype, incumbent)
                    or stale
                ):
                    decisions.append(
                        {
                            "type": "no_refinement_gain",
                            "candidate_id": candidate.candidate_id,
                            "incumbent": incumbent.semantic_rule_id,
                            "overlap_coefficient": overlap,
                        }
                    )
                    continue
                predecessor = replace(
                    new_latest[incumbent.semantic_rule_id],
                    lifecycle_state="refined_predecessor",
                    lifecycle_transition="refined",
                    valid_to=publication_effective_index,
                )
                new_latest[incumbent.semantic_rule_id] = predecessor
                history_by_id[incumbent.rule_revision_id] = predecessor
                prototype = replace(
                    prototype,
                    lineage_id=incumbent.lineage_id,
                    lifecycle_transition="refined",
                    parent_rule_revision_ids=(incumbent.rule_revision_id,),
                    parent_lineage_ids=(incumbent.lineage_id,),
                )
                decisions.append(
                    {
                        "type": "refined",
                        "candidate_id": candidate.candidate_id,
                        "predecessor": incumbent.semantic_rule_id,
                        "successor": semantic,
                        "overlap_coefficient": overlap,
                    }
                )
            else:
                prototype = replace(
                    prototype,
                    lifecycle_transition="new_addition",
                )
                decisions.append(
                    {
                        "type": "new_addition",
                        "candidate_id": candidate.candidate_id,
                        "semantic_rule_id": semantic,
                    }
                )

        ordinal += 1
        new_latest[semantic] = prototype
        history_by_id[prototype.rule_revision_id] = prototype
        masks[semantic] = candidate_mask

    changed = True
    while changed:
        changed = False
        active = sorted(
            active_latest().values(),
            key=lambda item: item.semantic_rule_id,
        )
        for i, left in enumerate(active):
            for right in active[i + 1 :]:
                left_mask = masks.get(left.semantic_rule_id)
                if left_mask is None:
                    left_mask = activation_mask(
                        X_validation,
                        feature_names=feature_names,
                        conditions=left.conditions,
                    )
                    masks[left.semantic_rule_id] = left_mask
                right_mask = masks.get(right.semantic_rule_id)
                if right_mask is None:
                    right_mask = activation_mask(
                        X_validation,
                        feature_names=feature_names,
                        conditions=right.conditions,
                    )
                    masks[right.semantic_rule_id] = right_mask
                overlap = overlap_statistics(left_mask, right_mask)
                coefficient = float(overlap["overlap_coefficient"])
                if left.consequent == right.consequent:
                    if coefficient < same_class_redundancy:
                        continue
                    winner = _same_class_winner(left, right)
                    loser = right if winner.semantic_rule_id == left.semantic_rule_id else left
                    updated_loser = replace(
                        loser,
                        lifecycle_state="merged",
                        lifecycle_transition="merge_consolidation",
                        valid_to=publication_effective_index,
                    )
                    new_latest[loser.semantic_rule_id] = updated_loser
                    history_by_id[loser.rule_revision_id] = updated_loser
                    decisions.append(
                        {
                            "type": "existing_same_class_consolidation",
                            "winner": winner.semantic_rule_id,
                            "merged": loser.semantic_rule_id,
                            **overlap,
                        }
                    )
                    changed = True
                    break

                if coefficient < cross_class_overlap:
                    continue
                if _pareto_revision_dominates(left, right):
                    winner, loser = left, right
                elif _pareto_revision_dominates(right, left):
                    winner, loser = right, left
                else:
                    continue
                updated_loser = replace(
                    loser,
                    lifecycle_state="demoted",
                    lifecycle_transition="cross_class_dominated",
                    failure_streak=max(1, loser.failure_streak),
                    valid_to=publication_effective_index,
                )
                new_latest[loser.semantic_rule_id] = updated_loser
                history_by_id[loser.rule_revision_id] = updated_loser
                decisions.append(
                    {
                        "type": "cross_class_dominated",
                        "winner": winner.semantic_rule_id,
                        "demoted": loser.semantic_rule_id,
                        **overlap,
                    }
                )
                changed = True
                break
            if changed:
                break

    final_active = sorted(
        (
            revision
            for revision in new_latest.values()
            if revision.lifecycle_state == "active"
        ),
        key=lambda item: item.semantic_rule_id,
    )

    # Rebuild unresolved cross-class relations from the surviving active set.
    # This avoids stale/duplicate relation accumulation across maintenance events.
    for revision in final_active:
        cleared = replace(revision, relations=())
        new_latest[revision.semantic_rule_id] = cleared
        history_by_id[revision.rule_revision_id] = cleared

    final_active = sorted(
        (
            revision
            for revision in new_latest.values()
            if revision.lifecycle_state == "active"
        ),
        key=lambda item: item.semantic_rule_id,
    )
    relation_map: dict[str, list[dict[str, Any]]] = {
        revision.semantic_rule_id: [] for revision in final_active
    }
    for index, left in enumerate(final_active):
        for right in final_active[index + 1 :]:
            if left.consequent == right.consequent:
                continue
            left_mask = masks.get(left.semantic_rule_id)
            if left_mask is None:
                left_mask = activation_mask(
                    X_validation,
                    feature_names=feature_names,
                    conditions=left.conditions,
                )
                masks[left.semantic_rule_id] = left_mask
            right_mask = masks.get(right.semantic_rule_id)
            if right_mask is None:
                right_mask = activation_mask(
                    X_validation,
                    feature_names=feature_names,
                    conditions=right.conditions,
                )
                masks[right.semantic_rule_id] = right_mask
            overlap = overlap_statistics(left_mask, right_mask)
            if float(overlap["overlap_coefficient"]) < cross_class_overlap:
                continue
            relation_map[left.semantic_rule_id].append(
                {
                    "type": "unresolved_cross_class_conflict",
                    "other": right.semantic_rule_id,
                    **overlap,
                }
            )
            relation_map[right.semantic_rule_id].append(
                {
                    "type": "unresolved_cross_class_conflict",
                    "other": left.semantic_rule_id,
                    **overlap,
                }
            )
            decisions.append(
                {
                    "type": "unresolved_cross_class_conflict",
                    "left": left.semantic_rule_id,
                    "right": right.semantic_rule_id,
                    **overlap,
                }
            )

    for revision in final_active:
        relations = tuple(
            sorted(
                relation_map[revision.semantic_rule_id],
                key=lambda item: (
                    str(item["type"]),
                    str(item["other"]),
                ),
            )
        )
        updated = replace(revision, relations=relations)
        new_latest[revision.semantic_rule_id] = updated
        history_by_id[revision.rule_revision_id] = updated

    final_active = sorted(
        (
            revision
            for revision in new_latest.values()
            if revision.lifecycle_state == "active"
        ),
        key=lambda item: item.semantic_rule_id,
    )

    previous_active_hash = _active_payload_hash(
        seed=state.seed,
        rule_base_version_id=state.rule_base_version_id,
        active_revisions=state.active_revisions(),
    )
    proposed_active_hash = _active_payload_hash(
        seed=state.seed,
        rule_base_version_id=state.rule_base_version_id,
        active_revisions=final_active,
    )
    published = previous_active_hash != proposed_active_hash

    effective_version_id = (
        target_version_id if published else state.rule_base_version_id
    )
    effective_version_number = (
        target_version_number if published else state.version_number
    )

    created_ids = {
        revision.rule_revision_id
        for revision in new_latest.values()
        if revision.rule_revision_id not in {
            old.rule_revision_id for old in state.revisions
        }
    }
    for revision_id in created_ids:
        current = history_by_id[revision_id]
        if current.rule_base_version_id != effective_version_id:
            updated = replace(
                current,
                rule_base_version_id=effective_version_id,
            )
            history_by_id[revision_id] = updated
            if new_latest.get(updated.semantic_rule_id, None) is current:
                new_latest[updated.semantic_rule_id] = updated

    final_active = sorted(
        (
            revision
            for revision in new_latest.values()
            if revision.lifecycle_state == "active"
        ),
        key=lambda item: item.semantic_rule_id,
    )
    normalized_revisions = tuple(
        sorted(
            history_by_id.values(),
            key=lambda item: (
                item.valid_from,
                item.semantic_rule_id,
                item.rule_revision_id,
            ),
        )
    )

    next_state = RuleBaseState(
        seed=state.seed,
        rule_base_version_id=effective_version_id,
        version_number=effective_version_number,
        parent_version_id=(
            state.rule_base_version_id if published else state.parent_version_id
        ),
        parent_version_sha256=(
            state.canonical_sha256 if published else state.parent_version_sha256
        ),
        revisions=normalized_revisions,
        active_revision_ids=tuple(
            item.rule_revision_id for item in final_active
        ),
        canonical_sha256=_active_payload_hash(
            seed=state.seed,
            rule_base_version_id=effective_version_id,
            active_revisions=final_active,
        ),
        history_sha256=_history_hash(normalized_revisions),
    )
    return LifecycleResult(
        state=next_state,
        published=published,
        maintenance_status=(
            "published" if published else "no_rule_base_change"
        ),
        decisions=tuple(decisions),
        staleness_snapshot=tuple(staleness),
        candidate_evidence=tuple(candidate_evidence),
    )


def active_rules_for_inference(
    state: RuleBaseState,
) -> tuple[Rule, ...]:
    return tuple(revision.to_rule() for revision in state.active_revisions())


def verify_lifecycle_state(state: RuleBaseState) -> None:
    revision_ids = [revision.rule_revision_id for revision in state.revisions]
    if len(revision_ids) != len(set(revision_ids)):
        raise ValueError("Duplicate rule revision ID.")
    lookup = {revision.rule_revision_id: revision for revision in state.revisions}
    for revision_id in state.active_revision_ids:
        if revision_id not in lookup:
            raise ValueError("Active rule revision is absent from history.")
        revision = lookup[revision_id]
        if revision.lifecycle_state != "active":
            raise ValueError("Non-active revision listed as inference-active.")
        if not revision.lineage_id:
            raise ValueError("Active rule lacks lineage identity.")
        if not revision.validation_evidence_id:
            raise ValueError("Active rule lacks validation evidence.")
        if not revision.neural_checkpoint_sha256:
            raise ValueError("Active rule lacks neural checkpoint identity.")
        if revision.valid_from < 0:
            raise ValueError("Active rule has invalid valid-from clock.")

    active = state.active_revisions()
    expected_active_hash = _active_payload_hash(
        seed=state.seed,
        rule_base_version_id=state.rule_base_version_id,
        active_revisions=active,
    )
    if expected_active_hash != state.canonical_sha256:
        raise ValueError("Rule-base canonical hash mismatch.")
    if _history_hash(state.revisions) != state.history_sha256:
        raise ValueError("Rule lifecycle-history hash mismatch.")



def rule_revision_from_dict(payload: Mapping[str, Any]) -> RuleRevision:
    conditions = tuple(
        Condition(
            feature=str(item["feature"]),
            operator=str(item["operator"]),
            threshold=float(item["threshold"]),
            raw_threshold=(
                float(item["raw_threshold"])
                if item.get("raw_threshold") is not None
                else None
            ),
        )
        for item in payload["conditions"]
    )
    return RuleRevision(
        semantic_rule_id=str(payload["semantic_rule_id"]),
        rule_revision_id=str(payload["rule_revision_id"]),
        lineage_id=str(payload["lineage_id"]),
        parent_rule_revision_ids=tuple(
            str(item) for item in payload["parent_rule_revision_ids"]
        ),
        parent_lineage_ids=tuple(
            str(item) for item in payload["parent_lineage_ids"]
        ),
        rule_base_version_id=str(payload["rule_base_version_id"]),
        seed=int(payload["seed"]),
        conditions=conditions,
        consequent=int(payload["consequent"]),
        confidence=float(payload["confidence"]),
        support=float(payload["support"]),
        covered_count=int(payload["covered_count"]),
        class_precision=float(payload["class_precision"]),
        class_precision_lcb=(
            float(payload["class_precision_lcb"])
            if payload.get("class_precision_lcb") is not None
            else None
        ),
        neural_fidelity=float(payload["neural_fidelity"]),
        neural_fidelity_lcb=(
            float(payload["neural_fidelity_lcb"])
            if payload.get("neural_fidelity_lcb") is not None
            else None
        ),
        stability=float(payload["stability"]),
        complexity=int(payload["complexity"]),
        lifecycle_state=str(payload["lifecycle_state"]),
        lifecycle_transition=str(payload["lifecycle_transition"]),
        failure_streak=int(payload["failure_streak"]),
        source_candidate_id=(
            str(payload["source_candidate_id"])
            if payload.get("source_candidate_id") is not None
            else None
        ),
        generation_evidence_id=(
            str(payload["generation_evidence_id"])
            if payload.get("generation_evidence_id") is not None
            else None
        ),
        validation_evidence_id=str(payload["validation_evidence_id"]),
        neural_checkpoint_sha256=str(
            payload["neural_checkpoint_sha256"]
        ),
        valid_from=int(payload["valid_from"]),
        valid_to=(
            int(payload["valid_to"])
            if payload.get("valid_to") is not None
            else None
        ),
        relations=tuple(dict(item) for item in payload.get("relations", ())),
    )


def rule_base_state_from_dict(payload: Mapping[str, Any]) -> RuleBaseState:
    state = RuleBaseState(
        seed=int(payload["seed"]),
        rule_base_version_id=str(payload["rule_base_version_id"]),
        version_number=int(payload["version_number"]),
        parent_version_id=(
            str(payload["parent_version_id"])
            if payload.get("parent_version_id") is not None
            else None
        ),
        parent_version_sha256=(
            str(payload["parent_version_sha256"])
            if payload.get("parent_version_sha256") is not None
            else None
        ),
        revisions=tuple(
            rule_revision_from_dict(item)
            for item in payload["revisions"]
        ),
        active_revision_ids=tuple(
            str(item) for item in payload["active_revision_ids"]
        ),
        canonical_sha256=str(payload["canonical_sha256"]),
        history_sha256=str(payload["history_sha256"]),
    )
    verify_lifecycle_state(state)
    return state
