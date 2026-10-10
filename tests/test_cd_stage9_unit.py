from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import inspect

import pytest

from concept_drift_ids import cd_stage9_config as config
from concept_drift_ids import cd_stage9_offline as offline
from concept_drift_ids import cd_stage9_phase_b as phase_b
from concept_drift_ids import cd_stage9_phase_c as phase_c
from concept_drift_ids import cd_stage9_export as export
from concept_drift_ids.cd_control_plane import MatureLabelRecord
from concept_drift_ids.cd_stage9_monitor import Stage9DriftMonitor
from concept_drift_ids.cd_stage9_phase_a import control_plane_for_condition
from concept_drift_ids.cd_stage9_shared_runner import Stage9ControlPlaneConfig


class _FakeDetector:
    def __init__(self, drift: bool = False) -> None:
        self.values: list[float] = []
        self.drift_detected = drift

    def update(self, value: float) -> None:
        self.values.append(float(value))


def _record(*, p: float, y: int, checkpoint: str = "cp") -> MatureLabelRecord:
    return MatureLabelRecord(
        row_id="stream:000001",
        origin_index=1,
        maturity_index=5001,
        checkpoint_sha256=checkpoint,
        neural_probability=p,
        true_label=y,
    )


def test_stage8_parent_two_level_config_identity_is_bound() -> None:
    assert (
        config.STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256
        == "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222"
    )
    assert (
        config.STAGE8_UPSTREAM_ARTIFACT_CONFIG_MANIFEST_SHA256
        == "3e3f768b5aa32f469440bb334508f747bbf2f7f5b08d9570a7aef2dbb9cb0257"
    )
    corrected, stored = config._canonical_manifest(config.STAGE8_CORRECTED_CONFIG_PATH)
    assert stored == config.STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256
    assert (
        corrected["upstream_artifact_config_manifest_sha256"]
        == config.STAGE8_UPSTREAM_ARTIFACT_CONFIG_MANIFEST_SHA256
    )


def test_actual_stage8_parent_bundle_verifies() -> None:
    parent = config._verify_stage8_parent()
    assert (
        parent["corrected_config_manifest_sha256"]
        == config.STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256
    )
    assert (
        parent["compact_export_manifest_sha256"]
        == config.STAGE8_COMPACT_EXPORT_MANIFEST_SHA256
    )
    assert (
        parent["confirmatory_aggregate_sha256"]
        == config.STAGE8_CONFIRMATORY_AGGREGATE_SHA256
    )

def test_condition_family_is_exactly_prespecified() -> None:
    specs = config._condition_specs(baseline_required=True)
    assert set(specs["offline"]) == {
        "lambda_0_7",
        "lambda_0_9",
        "lambda_1_0",
        "window_2500",
        "window_10000",
    }
    assert set(specs["symbolic_gate"]) == {"static_symbolic_gate"}
    assert set(specs["adaptive"]) == {
        "matched_primary_baseline",
        "latency_0",
        "latency_10000",
        "page_hinkley_hard_error",
        "adwin_brier",
        "no_replay",
    }


def test_page_hinkley_parameters_are_explicitly_frozen() -> None:
    assert config.PAGE_HINKLEY_CONFIG == {
        "min_instances": 30,
        "delta": 0.005,
        "threshold": 50.0,
        "alpha": 0.9999,
        "mode": "both",
    }



def test_page_hinkley_freeze_matches_locked_river_defaults() -> None:
    from river.drift import PageHinkley

    signature = inspect.signature(PageHinkley)
    for key, expected in config.PAGE_HINKLEY_CONFIG.items():
        assert key in signature.parameters
        assert signature.parameters[key].default == expected

def test_runtime_inventory_freezes_deterministic_torch_state() -> None:
    runtime = config._runtime_inventory()
    assert runtime["torch_cuda_available"] is False
    assert runtime["torch_deterministic_algorithms"] is True
    assert runtime["torch_num_threads"] == 1
    assert runtime["torch_num_interop_threads"] == 1
    assert runtime["configured_runtime"]["torch_deterministic_algorithms"] is True
    assert runtime["configured_runtime"]["torch_num_threads"] == 1
    assert runtime["configured_runtime"]["torch_num_interop_threads"] == 1

def test_runtime_difference_forces_matched_baseline() -> None:
    current = {
        "platform": "Linux-x",
        "processor": "x86",
        "python_version": "3.11.9",
        "python_implementation": "CPython",
        "torch_version": "2.14.1+cpu",
    }
    primary = {
        **current,
        "platform": "Windows-primary",
        "locked_distributions_sha256": "same",
    }
    assert config._runtime_requires_matched_baseline(
        current,
        primary,
        {"installed_distributions_sha256": "same"},
    )


def test_brier_monitor_uses_checkpoint_pure_delayed_probability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDetector()
    monkeypatch.setattr(Stage9DriftMonitor, "_new_detector", lambda self: fake)
    monitor = Stage9DriftMonitor(
        family="adwin",
        signal="brier",
        monitor_threshold=0.5,
    )
    monitor.start_initial_epoch("cp")
    obs = monitor.observe(_record(p=0.8, y=0))
    assert obs.admitted is True
    assert obs.signal_value == pytest.approx(0.64)
    assert fake.values == pytest.approx([0.64])


def test_hard_error_monitor_uses_frozen_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDetector()
    monkeypatch.setattr(Stage9DriftMonitor, "_new_detector", lambda self: fake)
    monitor = Stage9DriftMonitor(
        family="page_hinkley",
        signal="hard_error",
        monitor_threshold=0.7,
    )
    monitor.start_initial_epoch("cp")
    obs = monitor.observe(_record(p=0.69, y=1))
    assert obs.signal_value == 1.0
    assert fake.values == [1.0]


def test_stale_checkpoint_signal_is_never_admitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDetector()
    monkeypatch.setattr(Stage9DriftMonitor, "_new_detector", lambda self: fake)
    monitor = Stage9DriftMonitor(
        family="adwin",
        signal="hard_error",
        monitor_threshold=0.5,
    )
    monitor.start_initial_epoch("active")
    obs = monitor.observe(_record(p=0.9, y=1, checkpoint="old"))
    assert obs.admitted is False
    assert obs.signal_value is None
    assert fake.values == []


def test_no_replay_config_requires_zero_replay_budgets() -> None:
    bad = Stage9ControlPlaneConfig(
        replay_enabled=False,
        replay_anchor_rows=1,
        replay_online_rows=0,
    )
    with pytest.raises(ValueError, match="zero"):
        bad.validate()


def test_no_replay_condition_changes_only_replay_budget() -> None:
    frozen = {
        "conditions": config._condition_specs(baseline_required=True),
        "matched_baseline_required": True,
    }
    baseline = control_plane_for_condition("matched_primary_baseline", frozen)
    no_replay = control_plane_for_condition("no_replay", frozen)
    assert no_replay.label_latency == baseline.label_latency
    assert no_replay.detector_family == baseline.detector_family
    assert no_replay.detector_signal == baseline.detector_signal
    assert no_replay.current_window == baseline.current_window
    assert no_replay.neural_update == baseline.neural_update
    assert no_replay.replay_enabled is False
    assert no_replay.replay_anchor_rows == 0
    assert no_replay.replay_online_rows == 0


def test_latency_variants_change_only_latency() -> None:
    frozen = {
        "conditions": config._condition_specs(baseline_required=True),
        "matched_baseline_required": True,
    }
    baseline = control_plane_for_condition("matched_primary_baseline", frozen)
    zero = control_plane_for_condition("latency_0", frozen)
    tenk = control_plane_for_condition("latency_10000", frozen)
    assert zero.label_latency == 0
    assert tenk.label_latency == 10000
    for variant in (zero, tenk):
        assert variant.detector_family == baseline.detector_family
        assert variant.detector_signal == baseline.detector_signal
        assert variant.replay_enabled == baseline.replay_enabled
        assert variant.neural_update == baseline.neural_update


def test_static_gate_disables_wilson_requirements_without_changing_point_gate() -> None:
    operator = phase_b._operator_for_condition("static_symbolic_gate")
    gate = operator.gate
    assert gate.min_support == pytest.approx(0.001)
    assert gate.min_covered == 100
    assert gate.min_class_precision == pytest.approx(0.80)
    assert gate.min_neural_fidelity == pytest.approx(0.90)
    assert gate.min_precision_lcb == 0.0
    assert gate.min_fidelity_lcb == 0.0
    assert gate.min_stability == pytest.approx(0.90)
    assert gate.bootstrap_replicates == 100
    assert gate.max_complexity == 4


def test_latency_adjusted_trigger_delay_uses_active_condition_latency() -> None:
    events = [
        {
            "event_type": "drift_event",
            "status": "confirmed",
            "logical_clock": 80000,
        }
    ]
    zero = phase_c._trigger_diagnostics(events, label_latency=0)
    tenk = phase_c._trigger_diagnostics(events, label_latency=10000)
    assert zero["latency_adjusted_excess_delay_rows"] == 10740
    assert tenk["latency_adjusted_excess_delay_rows"] == 740


def test_offline_heavy_root_is_repository_artifacts_root() -> None:
    assert offline.PRIMARY_HEAVY_PHASE_C == (
        config.PROJECT_ROOT
        / "artifacts"
        / "cd_primary_v1"
        / "phase_c_offline_evaluation_v1_1"
    )


def test_config_preparation_declares_no_stage9_outcome_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "_require_clean_for_preparation", lambda: None)
    monkeypatch.setattr(
        config,
        "_verify_stage8_parent",
        lambda: {
            "corrected_config_manifest_sha256": "a",
            "compact_export_manifest_sha256": "b",
            "confirmatory_aggregate_sha256": "c",
        },
    )
    monkeypatch.setattr(
        config,
        "_requirements_identity",
        lambda: {"installed_distributions_sha256": "req"},
    )
    monkeypatch.setattr(
        config,
        "_runtime_inventory",
        lambda: {
            "platform": "x",
            "processor": "p",
            "python_version": "3.11.9",
            "python_implementation": "CPython",
            "torch_version": "t",
        },
    )
    monkeypatch.setattr(
        config,
        "_primary_runtime_reference",
        lambda: {
            "platform": "x",
            "processor": "p",
            "python_version": "3.11.9",
            "python_implementation": "CPython",
            "torch_version": "t",
            "locked_distributions_sha256": "req",
        },
    )
    monkeypatch.setattr(
        config,
        "_text_hashes",
        lambda paths: {path: f"hash:{path}" for path in paths},
    )
    monkeypatch.setattr(config, "_git_output", lambda *args: "source-head")
    payload = config.build_stage9_config()
    assert payload["stage9_outcomes_accessed_during_preparation"] is False
    assert payload["matched_baseline_required"] is False
    assert payload["prepared_from_git_commit"] == "source-head"


def test_config_freeze_requires_exact_parent_and_only_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = config.STAGE9_CONFIG_PATH.relative_to(config.PROJECT_ROOT).as_posix()
    responses = {
        ("rev-parse", "HEAD"): "freeze-head",
        ("diff-tree", "--no-commit-id", "--name-only", "-r", "freeze-head"): expected,
        ("show", "-s", "--format=%P", "freeze-head"): "source-head",
    }
    monkeypatch.setattr(config, "_git_output", lambda *args: responses[args])
    config._require_config_only_freeze({"prepared_from_git_commit": "source-head"})

    responses[("show", "-s", "--format=%P", "freeze-head")] = "wrong-parent"
    with pytest.raises(ValueError, match="parent"):
        config._require_config_only_freeze({"prepared_from_git_commit": "source-head"})


def test_offline_lambda_aggregate_reports_all_seed_contrasts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "c_frozen_symbolic": 0.70,
        "d_drift": 0.80,
        "d_periodic": 0.79,
    }

    def fake_condition(condition: str, seed: int, arm: str) -> dict[str, float]:
        base = values[arm] + 0.001 * seed
        return {
            "mcc": base,
            "f1": base,
            "fpr": 1.0 - base,
            "mcsc": 0.5,
            "resolved_coverage": 0.8,
        }

    def fake_reference(seed: int, arm: str) -> dict[str, float]:
        row = fake_condition("lambda_0_7", seed, arm)
        return {**row, "mcc": row["mcc"] - 0.01}

    monkeypatch.setattr(export, "_offline_lambda_metrics", fake_condition)
    monkeypatch.setattr(export, "_stage8_reference", fake_reference)
    payload = export._offline_condition_aggregate("lambda_0_7")

    assert payload["type"] == "fusion_authority_sensitivity"
    assert payload["adaptive_state_rerun"] is False
    assert payload["threshold_refit"] is False
    effect = payload["within_condition_primary_contrasts"]["d_drift_minus_c"]["mcc"]
    assert effect["values"] == pytest.approx([0.10] * 5)
    assert len(payload["arms"]["d_drift"]["mcc"]["values"]) == 5


def test_window_aggregate_does_not_redefine_whole_post_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        export,
        "_recovery_metric_summary",
        lambda condition, arm, metric: {
            "per_seed": [{"seed": seed} for seed in range(5)],
            "right_censored_count": 0,
        },
    )
    payload = export._offline_condition_aggregate("window_2500")
    assert payload["type"] == "reporting_window_sensitivity"
    assert payload["reporting_window_rows"] == 2500
    assert payload["whole_post_endpoints_changed"] is False
    assert set(payload["recovery"]) == set(phase_b.ARM_NAMES)
