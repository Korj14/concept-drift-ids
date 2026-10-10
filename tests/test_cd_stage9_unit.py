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
import concept_drift_ids.cd_stage9_shared_runner as stage9_runner
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
    specs = config._condition_specs(baseline_required=True, primary_contract_sha256="primary-contract")
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
        "torch_deterministic_algorithms": True,
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "thread_environment": dict(config.PRIMARY_THREAD_ENV),
    }
    primary_fingerprint = config._runtime_fingerprint(
        {**current, "platform": "Windows-primary"},
        locked_distributions_sha256="same",
    )
    assert config._runtime_requires_matched_baseline(
        current,
        {"common_fingerprint": primary_fingerprint},
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
        "conditions": config._condition_specs(baseline_required=True, primary_contract_sha256="primary-contract"),
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
        "conditions": config._condition_specs(baseline_required=True, primary_contract_sha256="primary-contract"),
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
    monkeypatch.setattr(config, "_require_stage8_closure_ancestor", lambda: None)
    monkeypatch.setattr(
        config, "_require_no_stage9_outputs_before_preparation", lambda: None
    )
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
    runtime = {
        "platform": "x",
        "processor": "p",
        "python_version": "3.11.9",
        "python_implementation": "CPython",
        "torch_version": "t",
        "torch_deterministic_algorithms": True,
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "thread_environment": dict(config.PRIMARY_THREAD_ENV),
    }
    monkeypatch.setattr(config, "_runtime_inventory", lambda: dict(runtime))
    fingerprint = config._runtime_fingerprint(
        runtime,
        locked_distributions_sha256="req",
    )
    monkeypatch.setattr(
        config,
        "_primary_runtime_reference",
        lambda: {
            "seed_fingerprints": {
                str(seed): dict(fingerprint) for seed in config.PRIMARY_SEEDS
            },
            "common_fingerprint": dict(fingerprint),
            "common_fingerprint_sha256": config.canonical_sha256(fingerprint),
        },
    )
    monkeypatch.setattr(
        config,
        "_stage8_frozen_primary_contract",
        lambda: {
            "source_config_manifest_sha256": "primary-config",
            "contract": {"primary": "contract"},
            "contract_sha256": "primary-contract",
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


def test_execution_worktree_allowance_is_compact_output_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[tuple[str, ...], str] = {
        ("status", "--porcelain"): "?? results/frozen/cd_robustness_v1/aggregate.json",
    }

    def fake_git_output(*args: str) -> str:
        if args in calls:
            return calls[args]
        raise RuntimeError("stop after worktree gate")

    monkeypatch.setattr(config, "_git_output", fake_git_output)
    monkeypatch.setattr(
        config,
        "load_stage9_config",
        lambda: (_ for _ in ()).throw(RuntimeError("stop after worktree gate")),
    )
    with pytest.raises(RuntimeError, match="stop after worktree gate"):
        config.verify_stage9_config_for_execution(
            allow_untracked_compact_output=True
        )

    calls[("status", "--porcelain")] = (
        "?? results/frozen/cd_robustness_v1/aggregate.json\n"
        "?? unrelated.txt"
    )
    with pytest.raises(RuntimeError, match="clean worktree"):
        config.verify_stage9_config_for_execution(
            allow_untracked_compact_output=True
        )


def test_stage9_portability_attributes_are_scoped() -> None:
    config_attr = (
        config.PROJECT_ROOT / "data" / "manifests" / ".gitattributes"
    ).read_text(encoding="utf-8")
    compact_attr = (
        config.PROJECT_ROOT / "results" / "frozen" / ".gitattributes"
    ).read_text(encoding="utf-8")
    assert "cd_stage9_run_config_v1.json text eol=lf" in config_attr
    assert "cd_robustness_v1/** text eol=lf" in compact_attr


def test_reused_stage8_computational_sources_are_historically_bound() -> None:
    corrected, _ = config._canonical_manifest(config.STAGE8_CORRECTED_CONFIG_PATH)
    frozen = corrected["scientific_source_hashes"]
    assert set(config.REUSED_STAGE8_SOURCE_PATHS).issubset(frozen)
    observed = config._verify_reused_stage8_source_tree(corrected)
    assert set(observed) == set(config.REUSED_STAGE8_SOURCE_PATHS)


def test_stage9_preparation_requires_stage8_closure_ancestor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Result:
        returncode = 1

    monkeypatch.setattr(config, "_git", lambda *args, **kwargs: Result())
    with pytest.raises(ValueError, match="Stage-8 closure"):
        config._require_stage8_closure_ancestor()


def test_stage9_preparation_refuses_preexisting_output_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    heavy = tmp_path / "heavy"
    compact = tmp_path / "compact"
    heavy.mkdir()
    monkeypatch.setattr(config, "STAGE9_OUTPUT_ROOT", heavy)
    monkeypatch.setattr(config, "STAGE9_COMPACT_ROOT", compact)
    with pytest.raises(RuntimeError, match="pre-existing robustness output"):
        config._require_no_stage9_outputs_before_preparation()


def test_primary_runtime_reference_requires_all_five_seeds_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_runtime = {
        "platform": "Windows-primary",
        "processor": "cpu",
        "python_version": "3.11.9",
        "python_implementation": "CPython",
        "torch_version": "2.14.1+cpu",
        "torch_deterministic_algorithms": True,
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "thread_environment": dict(config.PRIMARY_THREAD_ENV),
        "locked_distributions_sha256": "lock",
    }

    def fake_manifest(path: Path):
        seed = int(path.parent.name.split("-")[1])
        runtime = dict(base_runtime)
        if seed == 4:
            runtime["processor"] = "different-cpu"
        return {"runtime": runtime}, f"manifest-{seed}"

    monkeypatch.setattr(config, "_canonical_manifest", fake_manifest)
    with pytest.raises(ValueError, match="do not share one runtime"):
        config._primary_runtime_reference()


def test_primary_runtime_reference_records_all_five_seed_fingerprints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_runtime = {
        "platform": "Windows-primary",
        "processor": "cpu",
        "python_version": "3.11.9",
        "python_implementation": "CPython",
        "torch_version": "2.14.1+cpu",
        "torch_deterministic_algorithms": True,
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "thread_environment": dict(config.PRIMARY_THREAD_ENV),
        "locked_distributions_sha256": "lock",
    }
    monkeypatch.setattr(
        config,
        "_canonical_manifest",
        lambda path: ({"runtime": dict(base_runtime)}, "manifest"),
    )
    reference = config._primary_runtime_reference()
    assert set(reference["seed_fingerprints"]) == {"0", "1", "2", "3", "4"}
    assert reference["common_fingerprint_sha256"] == config.canonical_sha256(
        reference["common_fingerprint"]
    )


def test_frozen_primary_contract_is_bound_to_corrected_stage8_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = {
        "scenario": {"id": "scenario"},
        "system_a": {"id": "system-a"},
        "r0_v2": {"id": "r0"},
        "primary_control_plane": {"id": "cp"},
        "primary_symbolic_operator": {"id": "symbolic"},
        "fusion": {"id": "fusion"},
        "analysis": {"id": "analysis"},
    }
    monkeypatch.setattr(
        config,
        "_canonical_manifest",
        lambda path: (dict(source), config.STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256),
    )
    frozen = config._stage8_frozen_primary_contract()
    assert frozen["source_config_manifest_sha256"] == (
        config.STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256
    )
    assert frozen["contract"] == source
    assert frozen["contract_sha256"] == config.canonical_sha256(source)


def test_every_stage9_condition_is_bound_to_primary_contract_and_declares_changes() -> None:
    specs = config._condition_specs(
        baseline_required=True,
        primary_contract_sha256="primary-contract",
    )
    expected_changes = {
        "matched_primary_baseline": [],
        "latency_0": ["label_latency"],
        "latency_10000": ["label_latency"],
        "page_hinkley_hard_error": ["detector_family"],
        "adwin_brier": ["detector_signal"],
        "no_replay": ["replay_training_rows"],
        "lambda_0_7": ["fusion_neural_weight"],
        "lambda_0_9": ["fusion_neural_weight"],
        "lambda_1_0": ["fusion_neural_weight"],
        "window_2500": ["reporting_window_rows"],
        "window_10000": ["reporting_window_rows"],
        "static_symbolic_gate": ["symbolic_acceptance_gate"],
    }
    flattened = {
        **specs["adaptive"],
        **specs["offline"],
        **specs["symbolic_gate"],
    }
    assert set(flattened) == set(expected_changes)
    for name, spec in flattened.items():
        assert spec["base_primary_contract_sha256"] == "primary-contract"
        assert spec["changed_factors"] == expected_changes[name]


def test_prediction_before_label_event_order_accepts_same_clock_causal_order() -> None:
    events = [
        {"event_type": "prediction", "origin_index": 0, "logical_clock": 0},
        {"event_type": "label_release", "origin_index": 0, "logical_clock": 0},
        {
            "event_type": "detector_observation",
            "origin_index": 0,
            "logical_clock": 0,
        },
        {"event_type": "drift_event", "origin_index": 0, "logical_clock": 0},
    ]
    stage9_runner._verify_prediction_before_label_event_order(events)


def test_prediction_before_label_event_order_rejects_label_first() -> None:
    events = [
        {"event_type": "label_release", "origin_index": 0, "logical_clock": 0},
        {"event_type": "prediction", "origin_index": 0, "logical_clock": 0},
    ]
    with pytest.raises(ValueError, match="before prediction"):
        stage9_runner._verify_prediction_before_label_event_order(events)


def test_prediction_before_label_event_order_rejects_detector_before_label() -> None:
    events = [
        {"event_type": "prediction", "origin_index": 0, "logical_clock": 0},
        {
            "event_type": "detector_observation",
            "origin_index": 0,
            "logical_clock": 0,
        },
        {"event_type": "label_release", "origin_index": 0, "logical_clock": 0},
    ]
    with pytest.raises(ValueError, match="before mature-label"):
        stage9_runner._verify_prediction_before_label_event_order(events)


def test_static_gate_primary_config_reuse_requires_corrected_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        phase_b,
        "load_primary_run_config",
        lambda path: {"manifest_sha256": "wrong"},
    )
    with pytest.raises(ValueError, match="wrong corrected Stage-8 config"):
        phase_b._load_primary_corrected_config()


def test_export_verified_json_rejects_internal_hash_tamper(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.json"
    payload = {"value": 1}
    payload["summary_sha256"] = config.canonical_sha256(payload)
    from concept_drift_ids.cd_control_plane import write_json_new
    write_json_new(path, payload)

    loaded = export._read_verified_json(path, inner_hash_key="summary_sha256")
    assert loaded["value"] == 1

    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["value"] = 2
    # Recompute only the outer writer hash to simulate a file whose bytes look
    # self-consistent but whose scientific inner identity has changed.
    body = dict(tampered)
    body.pop("payload_sha256", None)
    tampered["payload_sha256"] = config.canonical_sha256(body)
    path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="summary_sha256"):
        export._read_verified_json(path, inner_hash_key="summary_sha256")


def test_numeric_summary_marks_t_interval_as_fixed_scenario_descriptive() -> None:
    summary = export._numeric_summary([1.0, 2.0, 3.0, 4.0, 5.0])
    assert "not_environmental" in summary["t95_interval_scope"]


def test_stage9_aggregate_inference_contract_has_no_new_pvalues() -> None:
    # This checks the frozen exporter source-level contract rather than outcomes.
    source = Path(export.__file__).read_text(encoding="utf-8")
    assert '"p_values_computed": False' in source
    assert '"all_frozen_conditions_reported": True' in source
    assert '"condition_selection_by_outcome_forbidden": True' in source
    assert '"reference_policy"' in source
