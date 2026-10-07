from __future__ import annotations

import inspect

from concept_drift_ids import system_b_dedup_teacher_robustness as robustness


def test_alternate_teacher_r0_uses_training_and_development_only() -> None:
    loader_source = inspect.getsource(robustness._load_train_dev_only)
    assert 'load_partition("training")' in loader_source
    assert 'load_partition("development")' in loader_source
    assert 'load_partition("pre_drift")' not in loader_source
    assert 'load_partition("post_drift")' not in loader_source


def test_alternate_teacher_r0_reconstructs_frozen_deduplicated_rows() -> None:
    source = inspect.getsource(robustness.build_pattern_dedup_teacher_r0)
    assert "verify_pattern_dedup_teacher()" in source
    assert "_deduplicated_training_indices" in source
    assert "retained_training_scenario_rows_sha256" in source
    assert "development_scenario_rows_sha256" in source
    assert "load_frozen_preprocessing()" in source
    assert '"preprocessing_refit": False' in source


def test_alternate_teacher_r0_is_write_once_and_cpu_frozen() -> None:
    source = inspect.getsource(robustness.build_pattern_dedup_teacher_r0)
    assert 'device_name != "cpu"' in source
    assert "OUTPUT_DIR.exists()" in source
    assert "_git_state(require_clean=True)" in source


def test_alternate_teacher_r0_verifier_checks_teacher_and_artifact_identity() -> None:
    source = inspect.getsource(robustness.verify_pattern_dedup_teacher_r0)
    assert "verify_pattern_dedup_teacher()" in source
    assert "source_alternate_teacher_manifest_sha256" in source
    assert "canonical_json_hash" in source
    assert "sha256_file" in source
