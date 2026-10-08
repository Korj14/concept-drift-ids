from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from sklearn.tree import DecisionTreeClassifier
from torch import nn

from concept_drift_ids.cd_control_plane import canonical_sha256
from concept_drift_ids.cd_symbolic_lifecycle import CandidateRule
from concept_drift_ids.symbolic import Condition, canonicalize_conditions


@dataclass(frozen=True)
class SymbolicGenerationConfig:
    background_per_class: int = 128
    attribution_per_class: int = 1_024
    selected_features: int = 12
    max_depth: int = 4
    min_samples_leaf: int = 100


@dataclass(frozen=True)
class CandidateGenerationResult:
    candidates: tuple[CandidateRule, ...]
    selected_features: tuple[str, ...]
    shap_ranking: tuple[dict[str, Any], ...]
    background_row_ids: tuple[str, ...]
    attribution_row_ids: tuple[str, ...]
    surrogate_seed: int
    generation_evidence_id: str
    timing_seconds: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [
                {
                    "candidate_id": item.candidate_id,
                    "seed": item.seed,
                    "antecedent": [
                        condition.to_dict() for condition in item.conditions
                    ],
                    "consequent": item.consequent,
                    "generation_evidence_id": item.generation_evidence_id,
                    "semantic_rule_id": item.semantic_rule_id,
                }
                for item in self.candidates
            ],
            "selected_features": list(self.selected_features),
            "shap_ranking": list(self.shap_ranking),
            "background_row_ids": list(self.background_row_ids),
            "attribution_row_ids": list(self.attribution_row_ids),
            "surrogate_seed": self.surrogate_seed,
            "generation_evidence_id": self.generation_evidence_id,
            "timing_seconds": dict(self.timing_seconds),
        }


class _LogitColumn(nn.Module):
    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x).unsqueeze(1)


def symbolic_seed_base(seed: int, opportunity_id: int) -> int:
    if opportunity_id <= 0:
        raise ValueError("opportunity_id must be one-based and positive.")
    return 20261020 + 1000 * int(seed) + 10 * int(opportunity_id)


def _balanced_sample_indices(
    y: np.ndarray,
    *,
    target_per_class: int,
    minimum_per_class: int,
    random_state: int,
) -> np.ndarray:
    y = np.asarray(y, dtype=np.int8)
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("Both true binary classes are required.")
    rng = np.random.default_rng(random_state)
    pieces: list[np.ndarray] = []
    for value in (0, 1):
        candidates = np.flatnonzero(y == value)
        if len(candidates) < minimum_per_class:
            raise ValueError(
                "candidate_generation_insufficient_class_evidence"
            )
        size = min(int(target_per_class), len(candidates))
        pieces.append(rng.choice(candidates, size=size, replace=False))
    return np.concatenate(pieces)


def select_online_shap_features(
    model: nn.Module,
    X: np.ndarray,
    y: np.ndarray,
    *,
    row_ids: Sequence[str],
    feature_names: Sequence[str],
    seed: int,
    opportunity_id: int,
    config: SymbolicGenerationConfig = SymbolicGenerationConfig(),
) -> tuple[
    tuple[str, ...],
    tuple[dict[str, Any], ...],
    tuple[str, ...],
    tuple[str, ...],
    float,
]:
    import shap

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int8)
    if X.ndim != 2 or X.shape[1] != len(feature_names):
        raise ValueError("Generation features do not match feature_names.")
    if len(X) != len(y) or len(X) != len(row_ids):
        raise ValueError("Generation row identities/features/labels mismatch.")
    if not np.isfinite(X).all():
        raise ValueError("Generation features must be finite.")

    base = symbolic_seed_base(seed, opportunity_id)
    background_idx = _balanced_sample_indices(
        y,
        target_per_class=config.background_per_class,
        minimum_per_class=config.background_per_class,
        random_state=base,
    )
    attribution_idx = _balanced_sample_indices(
        y,
        target_per_class=config.attribution_per_class,
        minimum_per_class=config.background_per_class,
        random_state=base + 1,
    )

    started = time.perf_counter_ns()
    wrapped = _LogitColumn(model.cpu()).eval()
    background = torch.from_numpy(X[background_idx])
    explained = torch.from_numpy(X[attribution_idx])
    explainer = shap.DeepExplainer(wrapped, background)
    values = np.asarray(
        explainer.shap_values(explained, check_additivity=True),
        dtype=np.float64,
    )
    if values.ndim == 3 and values.shape[-1] == 1:
        values = values[..., 0]
    expected_shape = (len(attribution_idx), len(feature_names))
    if values.shape != expected_shape:
        raise ValueError(
            f"Unexpected SHAP output shape: {values.shape}, "
            f"expected {expected_shape}."
        )
    if not np.isfinite(values).all():
        raise ValueError("SHAP returned non-finite values.")

    absolute = np.abs(values)
    sampled_y = y[attribution_idx]
    vectors = (
        absolute.mean(axis=0),
        absolute[sampled_y == 0].mean(axis=0),
        absolute[sampled_y == 1].mean(axis=0),
    )
    normalized: list[np.ndarray] = []
    for vector in vectors:
        maximum = float(vector.max())
        normalized.append(
            vector / maximum if maximum > 0 else np.zeros_like(vector)
        )
    score = np.maximum.reduce(normalized)
    order = sorted(
        range(len(feature_names)),
        key=lambda index: (-float(score[index]), index),
    )
    selected = tuple(
        str(feature_names[index])
        for index in order[: config.selected_features]
    )
    ranking = tuple(
        {
            "rank": rank + 1,
            "feature": str(feature_names[index]),
            "selection_score": float(score[index]),
            "mean_abs_shap_global": float(vectors[0][index]),
            "mean_abs_shap_benign": float(vectors[1][index]),
            "mean_abs_shap_attack": float(vectors[2][index]),
        }
        for rank, index in enumerate(order)
    )
    return (
        selected,
        ranking,
        tuple(str(row_ids[index]) for index in background_idx),
        tuple(str(row_ids[index]) for index in attribution_idx),
        (time.perf_counter_ns() - started) / 1_000_000_000.0,
    )


def fit_online_surrogate(
    X: np.ndarray,
    neural_decision: np.ndarray,
    *,
    feature_names: Sequence[str],
    selected_features: Sequence[str],
    random_state: int,
    config: SymbolicGenerationConfig = SymbolicGenerationConfig(),
) -> tuple[DecisionTreeClassifier, float]:
    X = np.asarray(X, dtype=np.float32)
    target = np.asarray(neural_decision, dtype=np.int8)
    if set(np.unique(target)) != {0, 1}:
        raise ValueError(
            "Both child-neural decision classes are required for surrogate fitting."
        )
    lookup = {name: index for index, name in enumerate(feature_names)}
    try:
        columns = [lookup[name] for name in selected_features]
    except KeyError as exc:
        raise ValueError(f"Unknown selected feature: {exc.args[0]}") from exc

    counts = np.bincount(target, minlength=2)
    sample_weight = np.where(
        target == 0,
        len(target) / (2.0 * counts[0]),
        len(target) / (2.0 * counts[1]),
    )
    tree = DecisionTreeClassifier(
        criterion="gini",
        splitter="best",
        max_depth=config.max_depth,
        min_samples_leaf=config.min_samples_leaf,
        random_state=int(random_state),
    )
    started = time.perf_counter_ns()
    tree.fit(X[:, columns], target, sample_weight=sample_weight)
    return tree, (time.perf_counter_ns() - started) / 1_000_000_000.0


def weighted_leaf_consequent(
    tree: DecisionTreeClassifier,
    leaf: int,
) -> int:
    values = np.asarray(
        tree.tree_.value[int(leaf)],
        dtype=np.float64,
    ).reshape(-1)
    classes = np.asarray(tree.classes_)
    if values.size != classes.size:
        raise ValueError("Unexpected surrogate leaf-value shape.")
    return int(classes[int(np.argmax(values))])


def tree_paths(
    tree: DecisionTreeClassifier,
    selected_features: Sequence[str],
) -> tuple[tuple[int, tuple[tuple[str, str, float], ...]], ...]:
    structure = tree.tree_
    out: list[tuple[int, tuple[tuple[str, str, float], ...]]] = []

    def walk(
        node: int,
        conditions: tuple[tuple[str, str, float], ...],
    ) -> None:
        left = int(structure.children_left[node])
        right = int(structure.children_right[node])
        if left == right:
            out.append((node, conditions))
            return
        feature = selected_features[int(structure.feature[node])]
        threshold = float(structure.threshold[node])
        walk(left, (*conditions, (feature, "<=", threshold)))
        walk(right, (*conditions, (feature, ">", threshold)))

    walk(0, ())
    return tuple(out)


def candidates_from_surrogate(
    tree: DecisionTreeClassifier,
    *,
    seed: int,
    opportunity_id: int,
    selected_features: Sequence[str],
    feature_names: Sequence[str],
    generation_evidence_id: str,
    raw_affine: Mapping[str, tuple[float, float]] | None = None,
) -> tuple[CandidateRule, ...]:
    out: list[CandidateRule] = []
    for leaf, path in tree_paths(tree, selected_features):
        canonical = canonicalize_conditions(
            path,
            feature_order=feature_names,
        )
        conditions: list[Condition] = []
        for item in canonical:
            raw_threshold = None
            if raw_affine is not None:
                mean, scale = raw_affine[item.feature]
                raw_threshold = item.threshold * float(scale) + float(mean)
            conditions.append(
                Condition(
                    feature=item.feature,
                    operator=item.operator,
                    threshold=float(item.threshold),
                    raw_threshold=raw_threshold,
                )
            )
        out.append(
            CandidateRule(
                candidate_id=(
                    f"d-s{seed}-m{opportunity_id}-leaf{int(leaf)}"
                ),
                seed=int(seed),
                conditions=tuple(conditions),
                consequent=weighted_leaf_consequent(tree, leaf),
                generation_evidence_id=str(generation_evidence_id),
            )
        )
    return tuple(out)


def generate_symbolic_candidates(
    model: nn.Module,
    X: np.ndarray,
    y: np.ndarray,
    neural_probability: np.ndarray,
    *,
    row_ids: Sequence[str],
    feature_names: Sequence[str],
    neural_threshold: float,
    seed: int,
    opportunity_id: int,
    raw_affine: Mapping[str, tuple[float, float]] | None = None,
    config: SymbolicGenerationConfig = SymbolicGenerationConfig(),
) -> CandidateGenerationResult:
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int8)
    neural_probability = np.asarray(neural_probability, dtype=np.float64)
    if len(X) != len(y) or len(y) != len(neural_probability):
        raise ValueError("Generation arrays have mismatched lengths.")
    if len(X) != len(row_ids):
        raise ValueError("Generation row IDs have mismatched length.")
    if not np.isfinite(neural_probability).all():
        raise ValueError("Neural probabilities must be finite.")
    if not 0.0 <= float(neural_threshold) <= 1.0:
        raise ValueError("neural_threshold must lie in [0,1].")

    (
        selected,
        ranking,
        background_ids,
        attribution_ids,
        shap_seconds,
    ) = select_online_shap_features(
        model,
        X,
        y,
        row_ids=row_ids,
        feature_names=feature_names,
        seed=seed,
        opportunity_id=opportunity_id,
        config=config,
    )
    base = symbolic_seed_base(seed, opportunity_id)
    neural_decision = (
        neural_probability >= float(neural_threshold)
    ).astype(np.int8)
    tree, surrogate_seconds = fit_online_surrogate(
        X,
        neural_decision,
        feature_names=feature_names,
        selected_features=selected,
        random_state=base + 2,
        config=config,
    )

    provisional = {
        "seed": int(seed),
        "opportunity_id": int(opportunity_id),
        "row_ids": list(row_ids),
        "background_row_ids": list(background_ids),
        "attribution_row_ids": list(attribution_ids),
        "selected_features": list(selected),
        "surrogate_random_state": base + 2,
        "config": asdict(config),
    }
    generation_evidence_id = canonical_sha256(provisional)
    candidates = candidates_from_surrogate(
        tree,
        seed=seed,
        opportunity_id=opportunity_id,
        selected_features=selected,
        feature_names=feature_names,
        generation_evidence_id=generation_evidence_id,
        raw_affine=raw_affine,
    )
    return CandidateGenerationResult(
        candidates=candidates,
        selected_features=selected,
        shap_ranking=ranking,
        background_row_ids=background_ids,
        attribution_row_ids=attribution_ids,
        surrogate_seed=base + 2,
        generation_evidence_id=generation_evidence_id,
        timing_seconds={
            "shap": float(shap_seconds),
            "surrogate": float(surrogate_seconds),
        },
    )
