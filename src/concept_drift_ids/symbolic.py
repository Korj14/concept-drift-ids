from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Iterable, Literal, Sequence

import numpy as np


Operator = Literal["<=", ">"]


@dataclass(frozen=True)
class Condition:
    feature: str
    operator: Operator
    threshold: float
    raw_threshold: float | None = None

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "feature": self.feature,
            "operator": self.operator,
            "threshold": float(self.threshold),
        }
        if self.raw_threshold is not None:
            out["raw_threshold"] = float(self.raw_threshold)
        return out


@dataclass(frozen=True)
class Rule:
    rule_id: str
    lineage_id: str
    rule_base_version: str
    seed: int
    conditions: tuple[Condition, ...]
    consequent: int
    confidence: float
    support: float
    covered_count: int
    class_precision: float
    neural_fidelity: float
    stability: float
    complexity: int
    lifecycle_state: str
    source_candidate_id: str
    validation_evidence_id: str
    relations: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "lineage_id": self.lineage_id,
            "rule_base_version": self.rule_base_version,
            "seed": int(self.seed),
            "antecedent": [item.to_dict() for item in self.conditions],
            "consequent": int(self.consequent),
            "confidence": float(self.confidence),
            "support": float(self.support),
            "covered_count": int(self.covered_count),
            "class_precision": float(self.class_precision),
            "neural_fidelity": float(self.neural_fidelity),
            "stability": float(self.stability),
            "complexity": int(self.complexity),
            "lifecycle_state": self.lifecycle_state,
            "source_candidate_id": self.source_candidate_id,
            "validation_evidence_id": self.validation_evidence_id,
            "relations": list(self.relations),
        }


def canonical_json_hash(payload: object) -> str:
    data = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonicalize_conditions(
    raw: Iterable[tuple[str, Operator, float]],
    *,
    feature_order: Sequence[str],
) -> tuple[Condition, ...]:
    rank = {name: i for i, name in enumerate(feature_order)}
    if len(rank) != len(feature_order):
        raise ValueError("feature_order contains duplicates.")
    bounds: dict[str, dict[str, float]] = {}
    for feature, operator, value in raw:
        if feature not in rank:
            raise ValueError(f"Unknown rule feature: {feature}")
        if operator not in {"<=", ">"}:
            raise ValueError(f"Unsupported operator: {operator}")
        threshold = float(value)
        if not np.isfinite(threshold):
            raise ValueError("Rule threshold must be finite.")
        item = bounds.setdefault(feature, {})
        if operator == ">":
            item[">"] = max(threshold, item.get(">", -np.inf))
        else:
            item["<="] = min(threshold, item.get("<=", np.inf))
    for feature, item in bounds.items():
        if ">" in item and "<=" in item and item[">"] >= item["<="]:
            raise ValueError(f"Contradictory bounds for feature {feature}.")
    out: list[Condition] = []
    for feature in sorted(bounds, key=rank.__getitem__):
        item = bounds[feature]
        if ">" in item:
            out.append(Condition(feature, ">", item[">"]))
        if "<=" in item:
            out.append(Condition(feature, "<=", item["<="]))
    return tuple(out)


def rule_identifier(*, seed: int, conditions: Sequence[Condition], consequent: int) -> str:
    core = {
        "seed": int(seed),
        "antecedent": [
            {"feature": c.feature, "operator": c.operator, "threshold": float(c.threshold)}
            for c in conditions
        ],
        "consequent": int(consequent),
    }
    return f"r0-s{seed}-{canonical_json_hash(core)[:16]}"


def activation_mask(
    X: np.ndarray,
    *,
    feature_names: Sequence[str],
    conditions: Sequence[Condition],
) -> np.ndarray:
    X = np.asarray(X)
    if X.ndim != 2 or X.shape[1] != len(feature_names):
        raise ValueError("X does not match feature_names.")
    lookup = {name: i for i, name in enumerate(feature_names)}
    mask = np.ones(len(X), dtype=bool)
    for condition in conditions:
        if condition.feature not in lookup:
            raise ValueError(f"Rule feature absent from X: {condition.feature}")
        values = X[:, lookup[condition.feature]]
        if condition.operator == "<=":
            mask &= values <= condition.threshold
        else:
            mask &= values > condition.threshold
    return mask


def rule_quality(
    mask: np.ndarray,
    *,
    y_true: np.ndarray,
    neural_decision: np.ndarray,
    consequent: int,
) -> dict[str, float | int]:
    mask = np.asarray(mask, dtype=bool)
    y_true = np.asarray(y_true, dtype=np.int8)
    neural_decision = np.asarray(neural_decision, dtype=np.int8)
    if not (len(mask) == len(y_true) == len(neural_decision)):
        raise ValueError("Rule-quality arrays have mismatched lengths.")
    covered = int(mask.sum())
    support = covered / len(mask) if len(mask) else 0.0
    precision = float(np.mean(y_true[mask] == consequent)) if covered else 0.0
    fidelity = float(np.mean(neural_decision[mask] == consequent)) if covered else 0.0
    return {
        "support": float(support),
        "covered_count": covered,
        "class_precision": precision,
        "neural_fidelity": fidelity,
    }


def stratified_bootstrap_indices(
    y: np.ndarray, *, replicates: int, random_state: int
) -> tuple[np.ndarray, ...]:
    y = np.asarray(y, dtype=np.int8)
    if replicates <= 0:
        raise ValueError("replicates must be positive.")
    groups = [np.flatnonzero(y == value) for value in (0, 1)]
    if any(len(group) == 0 for group in groups):
        raise ValueError("Both binary classes are required for stratified bootstrap.")
    rng = np.random.default_rng(random_state)
    return tuple(
        np.concatenate(
            [rng.choice(group, size=len(group), replace=True) for group in groups]
        )
        for _ in range(replicates)
    )


def bootstrap_gate_stability(
    mask: np.ndarray,
    *,
    y_true: np.ndarray,
    neural_decision: np.ndarray,
    consequent: int,
    bootstrap_indices: Sequence[np.ndarray],
    min_support: float,
    min_covered: int,
    min_precision: float,
    min_fidelity: float,
) -> float:
    passes = 0
    for idx in bootstrap_indices:
        idx = np.asarray(idx, dtype=np.int64)
        quality = rule_quality(
            np.asarray(mask, dtype=bool)[idx],
            y_true=np.asarray(y_true)[idx],
            neural_decision=np.asarray(neural_decision)[idx],
            consequent=consequent,
        )
        passes += int(
            quality["support"] >= min_support
            and quality["covered_count"] >= min_covered
            and quality["class_precision"] >= min_precision
            and quality["neural_fidelity"] >= min_fidelity
        )
    return passes / len(bootstrap_indices)


def overlap_statistics(left: np.ndarray, right: np.ndarray) -> dict[str, float | int]:
    left = np.asarray(left, dtype=bool)
    right = np.asarray(right, dtype=bool)
    if len(left) != len(right):
        raise ValueError("Overlap masks have mismatched lengths.")
    intersection = int(np.sum(left & right))
    union = int(np.sum(left | right))
    minimum = min(int(left.sum()), int(right.sum()))
    return {
        "intersection": intersection,
        "jaccard": intersection / union if union else 0.0,
        "overlap_coefficient": intersection / minimum if minimum else 0.0,
    }


def pareto_dominates(left: Rule, right: Rule) -> bool:
    weak = (
        left.class_precision >= right.class_precision
        and left.neural_fidelity >= right.neural_fidelity
        and left.support >= right.support
        and left.complexity <= right.complexity
    )
    strict = (
        left.class_precision > right.class_precision
        or left.neural_fidelity > right.neural_fidelity
        or left.support > right.support
        or left.complexity < right.complexity
    )
    return weak and strict


def apply_redundancy_and_conflict_policy(
    rules: Sequence[Rule],
    activation_masks: dict[str, np.ndarray],
    *,
    same_class_overlap: float,
    cross_class_overlap: float,
) -> tuple[list[Rule], list[dict[str, object]]]:
    active = list(rules)
    decisions: list[dict[str, object]] = []

    changed = True
    while changed:
        changed = False
        active.sort(key=lambda rule: rule.rule_id)
        for i, left in enumerate(active):
            for right in active[i + 1 :]:
                if left.consequent != right.consequent:
                    continue
                overlap = overlap_statistics(
                    activation_masks[left.rule_id], activation_masks[right.rule_id]
                )
                if float(overlap["overlap_coefficient"]) < same_class_overlap:
                    continue
                winner = sorted(
                    (left, right),
                    key=lambda r: (-r.confidence, -r.support, r.complexity, r.rule_id),
                )[0]
                loser = right if winner.rule_id == left.rule_id else left
                decisions.append(
                    {
                        "type": "same_class_redundancy",
                        "winner": winner.rule_id,
                        "rejected": loser.rule_id,
                        **overlap,
                    }
                )
                active = [r for r in active if r.rule_id != loser.rule_id]
                changed = True
                break
            if changed:
                break

    changed = True
    while changed:
        changed = False
        active.sort(key=lambda rule: rule.rule_id)
        for i, left in enumerate(active):
            for right in active[i + 1 :]:
                if left.consequent == right.consequent:
                    continue
                overlap = overlap_statistics(
                    activation_masks[left.rule_id], activation_masks[right.rule_id]
                )
                if float(overlap["overlap_coefficient"]) < cross_class_overlap:
                    continue
                if pareto_dominates(left, right):
                    winner, loser = left, right
                elif pareto_dominates(right, left):
                    winner, loser = right, left
                else:
                    decisions.append(
                        {
                            "type": "unresolved_cross_class_conflict",
                            "left": left.rule_id,
                            "right": right.rule_id,
                            **overlap,
                        }
                    )
                    continue
                decisions.append(
                    {
                        "type": "pareto_conflict_demotion",
                        "winner": winner.rule_id,
                        "rejected": loser.rule_id,
                        **overlap,
                    }
                )
                active = [r for r in active if r.rule_id != loser.rule_id]
                changed = True
                break
            if changed:
                break

    relations: dict[str, list[dict[str, object]]] = {
        rule.rule_id: [] for rule in active
    }
    for decision in decisions:
        for field in ("winner", "rejected", "left", "right"):
            value = decision.get(field)
            if isinstance(value, str) and value in relations:
                relations[value].append(decision)
    return [
        replace(rule, relations=tuple(relations[rule.rule_id])) for rule in active
    ], decisions


def infer_symbolic(
    X: np.ndarray,
    *,
    feature_names: Sequence[str],
    rules: Sequence[Rule],
) -> dict[str, np.ndarray]:
    rows = len(X)
    if not rules:
        return {
            "p_rule_attack": np.full(rows, np.nan),
            "covered": np.zeros(rows, dtype=bool),
            "uncovered": np.ones(rows, dtype=bool),
            "conflict_abstain": np.zeros(rows, dtype=bool),
            "raw_activated": np.zeros(rows, dtype=bool),
            "symbolic_class": np.full(rows, -1, dtype=np.int8),
            "activation_matrix": np.zeros((rows, 0), dtype=bool),
        }
    matrix = np.column_stack(
        [
            activation_mask(X, feature_names=feature_names, conditions=rule.conditions)
            for rule in rules
        ]
    )
    consequent = np.asarray([rule.consequent for rule in rules], dtype=np.int8)
    confidence = np.asarray([rule.confidence for rule in rules], dtype=np.float64)
    benign = np.any(matrix[:, consequent == 0], axis=1) if np.any(consequent == 0) else np.zeros(rows, bool)
    attack = np.any(matrix[:, consequent == 1], axis=1) if np.any(consequent == 1) else np.zeros(rows, bool)
    raw = np.any(matrix, axis=1)
    conflict = benign & attack
    covered = raw & ~conflict
    weighted = matrix * confidence[None, :]
    denom = weighted.sum(axis=1)
    attack_mass = weighted[:, consequent == 1].sum(axis=1) if np.any(consequent == 1) else np.zeros(rows)
    p_attack = np.full(rows, np.nan)
    valid = covered & (denom > 0)
    p_attack[valid] = attack_mass[valid] / denom[valid]
    symbolic_class = np.full(rows, -1, dtype=np.int8)
    symbolic_class[valid] = (p_attack[valid] >= 0.5).astype(np.int8)
    return {
        "p_rule_attack": p_attack,
        "covered": covered,
        "uncovered": ~raw,
        "conflict_abstain": conflict,
        "raw_activated": raw,
        "symbolic_class": symbolic_class,
        "activation_matrix": matrix,
    }


def fuse_scores(
    neural_attack_probability: np.ndarray,
    symbolic: dict[str, np.ndarray],
    *,
    neural_weight: float,
) -> np.ndarray:
    if not 0 <= neural_weight <= 1:
        raise ValueError("neural_weight must be in [0, 1].")
    neural = np.asarray(neural_attack_probability, dtype=np.float64)
    fused = neural.copy()
    covered = np.asarray(symbolic["covered"], dtype=bool)
    rule_score = np.asarray(symbolic["p_rule_attack"], dtype=np.float64)
    fused[covered] = (
        neural_weight * neural[covered] + (1 - neural_weight) * rule_score[covered]
    )
    return fused


def reporting_windows(
    n_rows: int, *, window_size: int = 5_000, min_remainder: int = 1_000
) -> tuple[tuple[int, int], ...]:
    if n_rows <= 0:
        return ()
    if window_size <= 0 or not 0 < min_remainder <= window_size:
        raise ValueError("Invalid reporting-window configuration.")
    windows = [
        (start, min(start + window_size, n_rows))
        for start in range(0, n_rows, window_size)
    ]
    if len(windows) >= 2 and windows[-1][1] - windows[-1][0] < min_remainder:
        windows[-2] = (windows[-2][0], windows[-1][1])
        windows.pop()
    return tuple(windows)
