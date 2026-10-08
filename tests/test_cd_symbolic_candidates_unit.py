from __future__ import annotations

import numpy as np
import pytest

from concept_drift_ids.cd_r0_lifecycle import (
    ACCEPTED_R0_V2_MANIFEST_SHA256,
    EXPECTED_ACTIVE_COUNTS,
    load_accepted_r0_v2_manifest,
    load_accepted_r0_v2_rules,
    migrate_accepted_r0_v2_state,
)
from concept_drift_ids.cd_symbolic_candidates import (
    SymbolicGenerationConfig,
    candidates_from_surrogate,
    fit_online_surrogate,
    symbolic_seed_base,
    tree_paths,
    weighted_leaf_consequent,
)
from concept_drift_ids.cd_symbolic_lifecycle import verify_lifecycle_state


def test_accepted_r0_v2_manifest_and_counts_are_pinned() -> None:
    manifest = load_accepted_r0_v2_manifest()
    assert manifest["manifest_sha256"] == ACCEPTED_R0_V2_MANIFEST_SHA256
    for seed, expected in EXPECTED_ACTIVE_COUNTS.items():
        rules = load_accepted_r0_v2_rules(seed)
        assert len(rules) == expected


def test_accepted_r0_v2_migrates_without_semantic_change() -> None:
    for seed, expected in EXPECTED_ACTIVE_COUNTS.items():
        source = load_accepted_r0_v2_rules(seed)
        state = migrate_accepted_r0_v2_state(
            seed,
            neural_checkpoint_sha256=f"checkpoint-{seed}",
        )
        verify_lifecycle_state(state)
        assert len(state.active_revision_ids) == expected
        migrated = state.active_revisions()
        assert {
            (
                tuple(
                    (c.feature, c.operator, c.threshold)
                    for c in revision.conditions
                ),
                revision.consequent,
                revision.confidence,
            )
            for revision in migrated
        } == {
            (
                tuple(
                    (c.feature, c.operator, c.threshold)
                    for c in rule.conditions
                ),
                rule.consequent,
                rule.confidence,
            )
            for rule in source
        }


def test_symbolic_seed_namespace_is_deterministic_and_separated() -> None:
    assert symbolic_seed_base(0, 1) == 20261030
    assert symbolic_seed_base(1, 1) == 20262030
    assert symbolic_seed_base(0, 2) == 20261040
    assert symbolic_seed_base(0, 1) != symbolic_seed_base(1, 1)


def test_surrogate_candidates_use_weighted_leaf_argmax() -> None:
    X = np.array(
        [
            [0.0, 0.0],
            [0.1, 0.1],
            [0.2, 0.2],
            [0.3, 0.3],
            [0.8, 0.8],
            [0.9, 0.9],
            [1.0, 1.0],
            [1.1, 1.1],
        ],
        dtype=np.float32,
    )
    neural = np.array([0, 0, 0, 1, 1, 1, 1, 1], dtype=np.int8)
    config = SymbolicGenerationConfig(
        selected_features=2,
        max_depth=2,
        min_samples_leaf=2,
    )
    tree, _ = fit_online_surrogate(
        X,
        neural,
        feature_names=("a", "b"),
        selected_features=("a", "b"),
        random_state=123,
        config=config,
    )
    candidates = candidates_from_surrogate(
        tree,
        seed=0,
        opportunity_id=1,
        selected_features=("a", "b"),
        feature_names=("a", "b"),
        generation_evidence_id="generation",
    )
    paths = tree_paths(tree, ("a", "b"))
    assert len(candidates) == len(paths)
    expected = {
        leaf: weighted_leaf_consequent(tree, leaf)
        for leaf, _ in paths
    }
    observed = {
        int(candidate.candidate_id.rsplit("leaf", 1)[1]): candidate.consequent
        for candidate in candidates
    }
    assert observed == expected


def test_surrogate_requires_both_neural_decision_classes() -> None:
    X = np.zeros((6, 2), dtype=np.float32)
    target = np.zeros(6, dtype=np.int8)
    with pytest.raises(ValueError, match="Both child-neural decision classes"):
        fit_online_surrogate(
            X,
            target,
            feature_names=("a", "b"),
            selected_features=("a",),
            random_state=1,
            config=SymbolicGenerationConfig(min_samples_leaf=2),
        )


def test_candidate_conditions_are_canonical_and_receive_raw_thresholds() -> None:
    X = np.array(
        [
            [0.0, 0.0],
            [0.1, 0.2],
            [0.2, 0.4],
            [0.8, 0.6],
            [0.9, 0.8],
            [1.0, 1.0],
        ],
        dtype=np.float32,
    )
    target = np.array([0, 0, 0, 1, 1, 1], dtype=np.int8)
    config = SymbolicGenerationConfig(
        selected_features=2,
        max_depth=2,
        min_samples_leaf=2,
    )
    tree, _ = fit_online_surrogate(
        X,
        target,
        feature_names=("a", "b"),
        selected_features=("a", "b"),
        random_state=2,
        config=config,
    )
    candidates = candidates_from_surrogate(
        tree,
        seed=0,
        opportunity_id=1,
        selected_features=("a", "b"),
        feature_names=("a", "b"),
        generation_evidence_id="generation",
        raw_affine={"a": (10.0, 2.0), "b": (20.0, 4.0)},
    )
    assert candidates
    for candidate in candidates:
        for condition in candidate.conditions:
            mean, scale = {"a": (10.0, 2.0), "b": (20.0, 4.0)}[
                condition.feature
            ]
            assert condition.raw_threshold == pytest.approx(
                condition.threshold * scale + mean
            )
