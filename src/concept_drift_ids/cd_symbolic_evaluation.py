from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from concept_drift_ids.cd_symbolic_lifecycle import (
    RuleBaseState,
    active_rules_for_inference,
)
from concept_drift_ids.neural import binary_metrics
from concept_drift_ids.symbolic import fuse_scores, infer_symbolic


PRIMARY_NEURAL_WEIGHT = 0.50

FUSION_THRESHOLDS = {
    0.50: {
        0: 0.692427396774292,
        1: 0.9354645609855652,
        2: 0.8299936652183533,
        3: 0.9747405052185059,
        4: 0.9527904391288757,
    },
    0.70: {
        0: 0.698998749256134,
        1: 0.9423287034034729,
        2: 0.8308807015419006,
        3: 0.9747405052185059,
        4: 0.9527904391288757,
    },
    0.90: {
        0: 0.9025245904922485,
        1: 0.9258511900901795,
        2: 0.8964613080024719,
        3: 0.9747405052185059,
        4: 0.9527904391288757,
    },
    1.00: {
        0: 0.9448108673095703,
        1: 0.9337316751480103,
        2: 0.9123510122299194,
        3: 0.9789738655090332,
        4: 0.9561389088630676,
    },
}


@dataclass(frozen=True)
class SymbolicArmEvaluation:
    neural_probability: np.ndarray
    symbolic_attack_probability: np.ndarray
    symbolic_class: np.ndarray
    covered: np.ndarray
    uncovered: np.ndarray
    conflict_abstain: np.ndarray
    fused_probability: np.ndarray
    thresholded_decision: np.ndarray
    metrics: Mapping[str, float]
    explanation: Mapping[str, float]


def fused_threshold(*, seed: int, neural_weight: float) -> float:
    if neural_weight not in FUSION_THRESHOLDS:
        raise ValueError("Unsupported frozen fusion sensitivity weight.")
    try:
        return float(FUSION_THRESHOLDS[neural_weight][int(seed)])
    except KeyError as exc:
        raise ValueError(f"Unsupported seed: {seed}") from exc


def macro_correct_symbolic_coverage(
    y_true: np.ndarray,
    symbolic: Mapping[str, np.ndarray],
) -> dict[str, float]:
    y = np.asarray(y_true, dtype=np.int8)
    covered = np.asarray(symbolic["covered"], dtype=bool)
    symbolic_class = np.asarray(symbolic["symbolic_class"], dtype=np.int8)
    conflict = np.asarray(symbolic["conflict_abstain"], dtype=bool)
    uncovered = np.asarray(symbolic["uncovered"], dtype=bool)
    if not (
        len(y)
        == len(covered)
        == len(symbolic_class)
        == len(conflict)
        == len(uncovered)
    ):
        raise ValueError("Explanation arrays have mismatched lengths.")

    result: dict[str, float] = {}
    correct_coverage: list[float] = []
    for value, name in ((0, "benign"), (1, "attack")):
        class_mask = y == value
        denominator = int(class_mask.sum())
        if denominator == 0:
            raise ValueError(
                "Both classes are required for macro correct symbolic coverage."
            )
        resolved_correct = class_mask & covered & (symbolic_class == value)
        class_coverage = float(np.mean(covered[class_mask]))
        class_correctness = (
            float(np.mean(symbolic_class[class_mask & covered] == value))
            if np.any(class_mask & covered)
            else 0.0
        )
        correct = float(resolved_correct.sum() / denominator)
        result[f"{name}_coverage"] = class_coverage
        result[f"{name}_symbolic_correctness_on_covered"] = class_correctness
        result[f"{name}_correct_symbolic_coverage"] = correct
        correct_coverage.append(correct)

    result["mcsc"] = float(np.mean(correct_coverage))
    result["resolved_coverage"] = float(np.mean(covered))
    result["uncovered_rate"] = float(np.mean(uncovered))
    result["conflict_abstain_rate"] = float(np.mean(conflict))
    return result


def evaluate_symbolic_arm(
    *,
    seed: int,
    X: np.ndarray,
    y_true: np.ndarray,
    neural_probability: np.ndarray,
    feature_names: Sequence[str],
    state: RuleBaseState,
    neural_weight: float = PRIMARY_NEURAL_WEIGHT,
) -> SymbolicArmEvaluation:
    X = np.asarray(X)
    y = np.asarray(y_true, dtype=np.int8)
    neural = np.asarray(neural_probability, dtype=np.float64)
    if len(X) != len(y) or len(y) != len(neural):
        raise ValueError("Arm-evaluation arrays have mismatched lengths.")
    if not np.isfinite(neural).all():
        raise ValueError("Neural probabilities must be finite.")

    rules = active_rules_for_inference(state)
    symbolic = infer_symbolic(
        X,
        feature_names=feature_names,
        rules=rules,
    )
    fused = fuse_scores(
        neural,
        symbolic,
        neural_weight=float(neural_weight),
    )
    threshold = fused_threshold(seed=seed, neural_weight=neural_weight)
    decision = (fused >= threshold).astype(np.int8)
    metrics = binary_metrics(y, fused, threshold)
    explanation = macro_correct_symbolic_coverage(y, symbolic)

    return SymbolicArmEvaluation(
        neural_probability=neural,
        symbolic_attack_probability=np.asarray(
            symbolic["p_rule_attack"],
            dtype=np.float64,
        ),
        symbolic_class=np.asarray(symbolic["symbolic_class"], dtype=np.int8),
        covered=np.asarray(symbolic["covered"], dtype=bool),
        uncovered=np.asarray(symbolic["uncovered"], dtype=bool),
        conflict_abstain=np.asarray(
            symbolic["conflict_abstain"],
            dtype=bool,
        ),
        fused_probability=fused,
        thresholded_decision=decision,
        metrics=metrics,
        explanation=explanation,
    )


def verify_lambda_one_negative_control(
    left: SymbolicArmEvaluation,
    right: SymbolicArmEvaluation,
) -> None:
    if not np.array_equal(
        left.neural_probability,
        right.neural_probability,
    ):
        raise ValueError("Matched arms do not share identical neural scores.")
    if not np.array_equal(
        left.fused_probability,
        right.fused_probability,
    ):
        raise ValueError(
            "Lambda=1 matched arms differ in predictive fused scores."
        )
    if not np.array_equal(
        left.thresholded_decision,
        right.thresholded_decision,
    ):
        raise ValueError(
            "Lambda=1 matched arms differ in thresholded predictions."
        )


def prediction_rows(
    evaluation: SymbolicArmEvaluation,
    *,
    row_ids: Sequence[str],
    seed: int,
    arm: str,
    checkpoint_ids: Sequence[str],
    rule_base_version_ids: Sequence[str],
    neural_weight: float,
) -> tuple[dict[str, Any], ...]:
    n = len(evaluation.neural_probability)
    if not (
        len(row_ids)
        == len(checkpoint_ids)
        == len(rule_base_version_ids)
        == n
    ):
        raise ValueError("Prediction provenance arrays have mismatched lengths.")
    threshold = fused_threshold(seed=seed, neural_weight=neural_weight)
    return tuple(
        {
            "row_id": str(row_ids[index]),
            "seed": int(seed),
            "arm": str(arm),
            "neural_probability": float(
                evaluation.neural_probability[index]
            ),
            "symbolic_attack_probability": (
                None
                if np.isnan(
                    evaluation.symbolic_attack_probability[index]
                )
                else float(
                    evaluation.symbolic_attack_probability[index]
                )
            ),
            "symbolic_class": int(evaluation.symbolic_class[index]),
            "covered": bool(evaluation.covered[index]),
            "uncovered": bool(evaluation.uncovered[index]),
            "conflict_abstain": bool(
                evaluation.conflict_abstain[index]
            ),
            "neural_weight": float(neural_weight),
            "fused_probability": float(
                evaluation.fused_probability[index]
            ),
            "threshold": threshold,
            "decision": int(evaluation.thresholded_decision[index]),
            "neural_checkpoint_sha256": str(checkpoint_ids[index]),
            "rule_base_version_id": str(rule_base_version_ids[index]),
        }
        for index in range(n)
    )
