from __future__ import annotations

from pathlib import Path

import pytest

from concept_drift_ids.cd_control_plane import (
    MatureLabelRecord,
    SharedErrorDriftMonitor,
)
from concept_drift_ids.cd_shared_runner import ControlPlaneConfig, SharedTrajectory
from concept_drift_ids import cd_stage9_config as config
from concept_drift_ids import cd_stage9_control_plane as control
from concept_drift_ids.cd_stage9_phase_a import condition_control_plane_config
from concept_drift_ids.symbolic import reporting_windows


def test_stage9_condition_family_is_frozen() -> None:
    assert set(config.CONDITIONS) == {
        "O_LAMBDA_070",
        "O_LAMBDA_090",
        "O_LAMBDA_100",
        "O_WINDOW_2500",
        "O_WINDOW_10000",
        "G_STATIC_GATE",
        "A_BASELINE",
        "A_LATENCY_0",
        "A_LATENCY_10000",
        "A_PAGE_HINKLEY",
        "A_ADWIN_BRIER",
        "A_NO_REPLAY",
    }
    assert config.CONDITIONS["A_LATENCY_0"]["label_latency"] == 0
    assert config.CONDITIONS["A_LATENCY_10000"]["label_latency"] == 10_000
    assert config.CONDITIONS["A_NO_REPLAY"]["replay"] == "none"
    assert config.CONDITIONS["O_LAMBDA_100"]["threshold_refit"] is False



def test_primary_stage9_control_plane_parameters_match_stage8_defaults() -> None:
    primary = ControlPlaneConfig()
    stage9 = control.Stage9ControlPlaneConfig()
    assert stage9.label_latency == primary.label_latency == 5_000
    assert stage9.current_window == primary.current_window == 10_000
    assert stage9.reservoir_capacity == primary.reservoir_capacity == 10_000
    assert stage9.replay_anchor_rows == primary.replay_anchor_rows == 5_000
    assert stage9.replay_online_rows == primary.replay_online_rows == 5_000
    assert stage9.neural_update == primary.neural_update
    assert stage9.detector_kind == "adwin_hard_error"


def test_primary_stage9_hard_error_monitor_matches_stage8_monitor() -> None:
    threshold = 0.7
    frozen = SharedErrorDriftMonitor(monitor_threshold=threshold)
    stage9 = control.Stage9DriftMonitor(
        monitor_threshold=threshold,
        detector_kind="adwin_hard_error",
    )
    frozen.start_initial_epoch("cp")
    stage9.start_initial_epoch("cp")

    for index in range(512):
        probability = 0.9 if index % 7 else 0.1
        label = 1 if index % 11 else 0
        record = MatureLabelRecord(
            row_id=f"r-{index}",
            origin_index=index,
            maturity_index=index + 5_000,
            checkpoint_sha256="cp",
            neural_probability=probability,
            true_label=label,
        )
        expected = frozen.observe(record)
        observed = stage9.observe(record)
        assert observed.row_id == expected.row_id
        assert observed.origin_index == expected.origin_index
        assert observed.maturity_index == expected.maturity_index
        assert observed.epoch_id == expected.epoch_id
        assert observed.epoch_checkpoint_sha256 == expected.epoch_checkpoint_sha256
        assert (
            observed.prediction_checkpoint_sha256
            == expected.prediction_checkpoint_sha256
        )
        assert observed.admitted == expected.admitted
        assert observed.drift_detected == expected.drift_detected
        assert observed.reason == expected.reason
        assert observed.hard_error == expected.error
        assert observed.signal == (
            None if expected.error is None else float(expected.error)
        )

def test_page_hinkley_uses_explicit_river_0261_defaults() -> None:
    assert config.PAGE_HINKLEY_CONFIG == {
        "min_instances": 30,
        "delta": 0.005,
        "threshold": 50.0,
        "alpha": 0.9999,
        "mode": "both",
    }
    monitor = control.Stage9DriftMonitor(
        monitor_threshold=0.5,
        detector_kind="page_hinkley_hard_error",
    )
    detector = monitor._new_detector()
    assert detector.min_instances == 30
    assert detector.delta == 0.005
    assert detector.threshold == 50.0
    assert detector.alpha == 0.9999
    assert detector.mode == "both"


def test_static_gate_removes_only_lcb_requirement() -> None:
    gate = config.STATIC_GATE
    assert gate.min_support == 0.001
    assert gate.min_covered == 100
    assert gate.min_class_precision == 0.80
    assert gate.min_neural_fidelity == 0.90
    assert gate.bootstrap_replicates == 100
    assert gate.min_stability == 0.90
    assert gate.max_complexity == 4
    assert gate.min_precision_lcb == 0.0
    assert gate.min_fidelity_lcb == 0.0


def test_runtime_mismatch_makes_stage9_baseline_mandatory() -> None:
    primary = {
        "platform": "Windows",
        "processor": "cpu-a",
        "python_implementation": "CPython",
        "python_version": "3.11.9",
        "locked_distributions_sha256": "lock",
        "torch_version": "2.14.1+cpu",
        "torch_deterministic_algorithms": True,
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "thread_environment": dict(config.PRIMARY_THREAD_ENV),
        "threadpool_info": [],
    }
    same = dict(primary)
    result = config._runtime_comparison(primary, same)
    assert result["materially_identical"] is True
    assert result["matched_stage9_baseline_required"] is False

    changed = dict(primary)
    changed["platform"] = "Linux-x86_64"
    result = config._runtime_comparison(primary, changed)
    assert result["materially_identical"] is False
    assert result["matched_stage9_baseline_required"] is True
    assert "platform" in result["mismatches"]


def test_stale_checkpoint_detector_observation_is_never_admitted() -> None:
    monitor = control.Stage9DriftMonitor(
        monitor_threshold=0.5,
        detector_kind="adwin_hard_error",
    )
    monitor.start_initial_epoch("active")
    record = MatureLabelRecord(
        row_id="r",
        origin_index=0,
        maturity_index=5_000,
        checkpoint_sha256="stale",
        neural_probability=0.9,
        true_label=1,
    )
    observation = monitor.observe(record)
    assert observation.admitted is False
    assert observation.signal is None
    assert observation.hard_error is None
    assert observation.reason == "stale_checkpoint_observation"


def test_brier_signal_uses_committed_probability_and_mature_label() -> None:
    monitor = control.Stage9DriftMonitor(
        monitor_threshold=0.5,
        detector_kind="adwin_brier",
    )
    monitor.start_initial_epoch("cp")
    record = MatureLabelRecord(
        row_id="r",
        origin_index=10,
        maturity_index=5_010,
        checkpoint_sha256="cp",
        neural_probability=0.8,
        true_label=1,
    )
    observation = monitor.observe(record)
    assert observation.admitted is True
    assert observation.hard_error == 0
    assert observation.signal == pytest.approx(0.04)


def test_hard_error_signal_is_thresholded_stored_prediction() -> None:
    monitor = control.Stage9DriftMonitor(
        monitor_threshold=0.7,
        detector_kind="adwin_hard_error",
    )
    monitor.start_initial_epoch("cp")
    observation = monitor.observe(
        MatureLabelRecord(
            row_id="r",
            origin_index=0,
            maturity_index=5_000,
            checkpoint_sha256="cp",
            neural_probability=0.69,
            true_label=1,
        )
    )
    assert observation.admitted is True
    assert observation.signal == 1.0
    assert observation.hard_error == 1


def test_no_replay_condition_maps_to_zero_replay_budget() -> None:
    fake_config = {
        "conditions": {
            "A_NO_REPLAY": {
                "label_latency": 5_000,
                "replay": "none",
                "detector": "adwin_hard_error",
            }
        }
    }
    cp = condition_control_plane_config("A_NO_REPLAY", fake_config)
    assert cp.replay_mode == "none"
    assert cp.replay_anchor_rows == 0
    assert cp.replay_online_rows == 0
    cp.validate()


def test_no_replay_verifier_rejects_any_replay_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control, "verify_shared_trajectory", lambda *a, **k: None)
    cp = control.Stage9ControlPlaneConfig(replay_mode="none")
    current = [f"c-{i}" for i in range(10_000)]
    trajectory = SharedTrajectory(
        seed=0,
        config_sha256="cfg",
        predictions=(),
        label_schedule=(),
        detector_observations=(),
        events=(),
        replay_transactions=(
            {
                "condition_id": "A_NO_REPLAY",
                "detector_kind": "adwin_hard_error",
                "replay_mode": "none",
                "current_row_ids": current,
                "replay_row_ids": ["forbidden"],
            },
        ),
        checkpoint_chain=(),
        shared_identity={},
        final_checkpoint_sha256="cp",
        final_state_sha256="state",
        pending_labels=0,
        pending_neural_transaction=None,
    )
    with pytest.raises(ValueError, match="No-replay transaction"):
        control.verify_stage9_shared_trajectory(
            trajectory,
            config=cp,
            condition_id="A_NO_REPLAY",
        )


def test_stage9_config_preparation_flags_outcome_blind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "_require_clean_worktree", lambda **kwargs: None)
    monkeypatch.setattr(
        config,
        "_verify_parent_compact_evidence",
        lambda: {
            "compact_export_manifest_sha256": (
                config.PARENT_COMPACT_EXPORT_MANIFEST_SHA256
            ),
            "confirmatory_aggregate_sha256": (
                config.PARENT_CONFIRMATORY_AGGREGATE_SHA256
            ),
        },
    )
    monkeypatch.setattr(
        config,
        "_verify_parent_primary_config",
        lambda: {
            "scenario": {
                "scenario_id": "cicids2017_sudden_benign_v1",
                "scenario_version": 1,
                "manifest_canonical_sha256": "scenario",
                "preprocessing_state_hash": "preprocessing",
                "stream_rows": 138_530,
            }
        },
    )
    monkeypatch.setattr(config, "_git_output", lambda *a, **k: "source-head")
    monkeypatch.setattr(
        config,
        "_source_hashes",
        lambda **kwargs: {"stage9.py": "source"},
    )
    runtime = {
        "platform": "same",
        "processor": "same",
        "python_implementation": "CPython",
        "python_version": "3.11.9",
        "locked_distributions_sha256": "lock",
        "torch_version": "2.14.1+cpu",
        "torch_deterministic_algorithms": True,
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "thread_environment": dict(config.PRIMARY_THREAD_ENV),
        "threadpool_info": [],
    }
    monkeypatch.setattr(config, "_primary_runtime", lambda: runtime)
    monkeypatch.setattr(config, "_current_runtime", lambda: runtime)
    monkeypatch.setattr(config, "sha256_file", lambda path: "hash")

    payload = config.build_stage9_config()
    assert payload["preparation"] == {
        "primary_partitions_loaded": False,
        "heavy_phase_c_traces_loaded": False,
        "stage9_treatment_executed": False,
        "stage9_outcome_accessed": False,
    }
    assert (
        payload["conditions"]["A_BASELINE"]["required"]
        is False
    )


def test_stage9_config_only_freeze_commit_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = {"source_commit": "source-head"}

    def good_git_output(*args: str, **kwargs: object) -> str:
        if args[:2] == ("rev-parse", "HEAD"):
            return "config-head"
        if args[:3] == ("log", "-1", "--format=%H"):
            return "config-head"
        if args[:3] == ("show", "-s", "--format=%P"):
            return "source-head"
        if args[:3] == ("diff-tree", "--no-commit-id", "--name-only"):
            return "data/manifests/cd_stage9_run_config_v1.json"
        raise AssertionError(args)

    monkeypatch.setattr(config, "_git_output", good_git_output)
    assert config._require_exact_config_commit(frozen) == "config-head"

    def bad_git_output(*args: str, **kwargs: object) -> str:
        value = good_git_output(*args, **kwargs)
        if args[:3] == ("diff-tree", "--no-commit-id", "--name-only"):
            return value + "\nextra.txt"
        return value

    monkeypatch.setattr(config, "_git_output", bad_git_output)
    with pytest.raises(RuntimeError, match="must change exactly"):
        config._require_exact_config_commit(frozen)


def test_reporting_window_sensitivities_keep_minimum_remainder_rule() -> None:
    for size in (2_500, 10_000):
        windows = reporting_windows(
            69_270,
            window_size=size,
            min_remainder=1_000,
        )
        assert all(stop > start for start, stop in windows)
        assert windows[0][0] == 0
        assert windows[-1][1] == 69_270
        assert windows[-1][1] - windows[-1][0] >= 1_000
