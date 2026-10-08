from __future__ import annotations

import inspect

from concept_drift_ids import system_b_dedup_teacher_evaluation as evaluation


def test_pattern_dedup_chain_evaluator_loads_held_out_only() -> None:
    loader = inspect.getsource(evaluation._load_evaluation_partitions)
    assert 'load_partition("pre_drift")' in loader
    assert 'load_partition("post_drift")' in loader
    assert 'load_partition("training")' not in loader
    assert 'load_partition("development")' not in loader


def test_pattern_dedup_chain_evaluator_is_write_once_cpu_and_clean_git() -> None:
    source = inspect.getsource(evaluation.evaluate_pattern_dedup_training_chain)
    assert 'device_name != "cpu"' in source
    assert "OUTPUT_DIR.exists()" in source
    assert "_git_state(require_clean=True)" in source


def test_pattern_dedup_chain_evaluator_verifies_frozen_sources() -> None:
    source = inspect.getsource(evaluation.evaluate_pattern_dedup_training_chain)
    assert "verify_pattern_dedup_teacher()" in source
    assert "verify_pattern_dedup_teacher_r0()" in source
    assert "source_alternate_teacher_manifest_sha256" in source
    assert "preprocessing_state_hash" in source


def test_pattern_dedup_chain_evaluator_scores_both_alternate_systems() -> None:
    source = inspect.getsource(evaluation.evaluate_pattern_dedup_training_chain)
    assert "ALT_A_ID" in source
    assert "ALT_B_ID" in source
    assert "binary_metrics" in source
    assert "infer_symbolic" in source
    assert "fuse_scores" in source
    assert "_symbolic_summary" in source


def test_pattern_dedup_chain_verifier_checks_source_and_file_hashes() -> None:
    source = inspect.getsource(evaluation.verify_pattern_dedup_training_chain_evaluation)
    assert "source_alternate_teacher_manifest_sha256" in source
    assert "source_alternate_r0_manifest_sha256" in source
    assert "canonical_json_hash" in source
    assert "sha256_file" in source


def test_pattern_dedup_chain_rectangularizes_mixed_system_rows() -> None:
    rows = [
        {
            "system_id": evaluation.ALT_A_ID,
            "partition": "pre_drift",
            "seed": 0,
            "accuracy": 0.9,
        },
        {
            "system_id": evaluation.ALT_B_ID,
            "partition": "pre_drift",
            "seed": 0,
            "accuracy": 0.91,
            "resolved_coverage": 0.8,
            "attack_symbolic_correctness": 0.7,
        },
    ]

    rectangular = evaluation._rectangularize_rows(rows)

    assert list(rectangular[0]) == list(rectangular[1])
    assert rectangular[0]["resolved_coverage"] is None
    assert rectangular[0]["attack_symbolic_correctness"] is None
    assert rectangular[1]["resolved_coverage"] == 0.8
    assert rectangular[1]["attack_symbolic_correctness"] == 0.7
