from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_evidence import (
    build_run_manifest,
    build_shared_identity,
    read_jsonl,
    records_sha256,
    validate_event,
    verify_checkpoint_chain,
    verify_manifest_files,
)
from concept_drift_ids.cd_primary_adapter import build_primary_input_bundle
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_stage9_config import (
    ADAPTIVE_VARIANTS,
    MATCHED_BASELINE_CONDITION,
    PRIMARY_SEEDS,
    STAGE9_OUTPUT_ROOT,
    STAGE9_RUN_ID,
    _git_output,
    artifact_identity_context,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_shared_runner import (
    Stage9ControlPlaneConfig,
    Stage9SharedControlPlaneRunner,
    freeze_stage9_shared_trajectory,
    verify_stage9_control_plane_configuration,
    verify_stage9_shared_trajectory,
)
from concept_drift_ids.scenario_manifest import sha256_file


def adaptive_condition_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    ids = list(ADAPTIVE_VARIANTS)
    if bool(config["matched_baseline_required"]):
        ids.insert(0, MATCHED_BASELINE_CONDITION)
    return tuple(ids)


def _seed_dir(condition: str, seed: int) -> Path:
    return (
        STAGE9_OUTPUT_ROOT
        / condition
        / "phase_a_shared_control_plane"
        / f"seed-{seed}"
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_manifest_hash(manifest: dict[str, Any]) -> None:
    body = dict(manifest)
    body.pop("payload_sha256", None)
    stored = body.pop("manifest_sha256", None)
    if stored != canonical_sha256(body):
        raise ValueError("Stage-9 Phase-A run manifest canonical hash mismatch.")


def _child_checkpoint_descriptors(seed_dir: Path) -> dict[str, dict[str, str]]:
    checkpoint_dir = seed_dir / "checkpoints"
    if not checkpoint_dir.exists():
        return {}
    files: dict[str, dict[str, str]] = {}
    for index, path in enumerate(sorted(checkpoint_dir.glob("*.pt")), start=1):
        files[f"child_checkpoint_{index:04d}"] = {
            "path": path.relative_to(seed_dir).as_posix(),
            "sha256": sha256_file(path),
        }
    return files


def control_plane_for_condition(
    condition: str,
    config: Mapping[str, Any],
) -> Stage9ControlPlaneConfig:
    specs = config["conditions"]["adaptive"]
    if condition not in specs:
        raise ValueError(f"Condition is not frozen as adaptive Stage-9 work: {condition}")
    spec = specs[condition]
    replay = bool(spec["replay_enabled"])
    return Stage9ControlPlaneConfig(
        label_latency=int(spec["label_latency"]),
        replay_anchor_rows=5000 if replay else 0,
        replay_online_rows=5000 if replay else 0,
        detector_family=str(spec["detector_family"]),
        detector_signal=str(spec["detector_signal"]),
        detector_config=spec.get("detector_config"),
        replay_enabled=replay,
    )


def execute_stage9_phase_a_seed(condition: str, seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")
    config = verify_stage9_config_for_execution()
    if condition not in adaptive_condition_ids(config):
        raise ValueError(f"Unsupported/disabled Stage-9 adaptive condition: {condition}")

    runtime = configure_torch_primary_runtime()
    cp_config = control_plane_for_condition(condition, config)
    seed_dir = _seed_dir(condition, seed)
    if seed_dir.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 Phase-A output: {seed_dir}")
    seed_dir.mkdir(parents=True, exist_ok=False)

    attempt = {
        "run_id": f"{STAGE9_RUN_ID}-{condition}-phase-a-seed-{seed}",
        "condition_id": condition,
        "seed": seed,
        "git_commit": _git_output("rev-parse", "HEAD"),
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "boundary_metadata_passed_to_runner": False,
        "scoring_performed": False,
        "symbolic_arms_executed": False,
        "identity_context": artifact_identity_context(
            config, condition=condition, seed=seed
        ),
    }
    write_json_new(seed_dir / "attempt.json", attempt)

    try:
        bundle = build_primary_input_bundle(seed)
        verify_stage9_control_plane_configuration(
            seed=seed,
            monitor_threshold=bundle.monitor_threshold,
            anchor_row_count=len(bundle.anchor_rows),
            config=cp_config,
        )
        input_identity_sha256 = write_json_new(
            seed_dir / "input_identity.json", bundle.audit_identity
        )
        runner = Stage9SharedControlPlaneRunner(
            seed=seed,
            initial_model=bundle.model,
            initial_checkpoint_sha256=bundle.initial_checkpoint_sha256,
            monitor_threshold=bundle.monitor_threshold,
            anchor_rows=bundle.anchor_rows,
            checkpoint_dir=seed_dir / "checkpoints",
            run_id=f"{STAGE9_RUN_ID}-{condition}-phase-a-seed-{seed}",
            git_commit=_git_output("rev-parse", "HEAD"),
            config=cp_config,
        )
        trajectory = runner.run(bundle.stream_rows)
        verify_stage9_shared_trajectory(
            trajectory,
            label_latency=cp_config.label_latency,
        )
        files = freeze_stage9_shared_trajectory(seed_dir, trajectory)
        files["input_identity"] = {
            "path": "input_identity.json",
            "sha256": input_identity_sha256,
        }
        files.update(_child_checkpoint_descriptors(seed_dir))

        manifest = build_run_manifest(
            run_id=f"{STAGE9_RUN_ID}-{condition}-phase-a-seed-{seed}",
            seed=seed,
            git_commit=_git_output("rev-parse", "HEAD"),
            protocol_hashes={
                config["protocol"]["path"]: config["protocol"]["sha256"]
            },
            runtime=runtime,
            scenario_identity={
                "stage9_config_manifest_sha256": config["manifest_sha256"],
                "stage8_parent": config["stage8_parent"],
                "condition_id": condition,
                "condition_spec": config["conditions"]["adaptive"][condition],
                "scenario": config["scenario"],
                "input_identity": bundle.audit_identity,
                "adaptive_runner_received_boundary_metadata": False,
                "artifact_identity_context": artifact_identity_context(
                    config, condition=condition, seed=seed
                ),
            },
            initial_checkpoint_sha256=bundle.initial_checkpoint_sha256,
            preprocessing_sha256=bundle.preprocessing_state_hash,
            files=files,
            status="complete_unscored_stage9_shared_trajectory",
        )
        write_json_new(seed_dir / "run_manifest.json", manifest)
        verify_manifest_files(seed_dir, manifest)
        verify_stage9_phase_a_seed(condition, seed, config=config)
    except Exception as exc:
        failure_path = seed_dir / "failure.json"
        if not failure_path.exists():
            write_json_new(
                failure_path,
                {
                    "condition_id": condition,
                    "seed": seed,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "scoring_performed": False,
                    "symbolic_arms_executed": False,
                    "identity_context": artifact_identity_context(
                        config, condition=condition, seed=seed
                    ),
                },
            )
        raise

    return {
        "status": "stage9_phase_a_seed_complete_unscored",
        "condition_id": condition,
        "seed": seed,
        "run_manifest_sha256": manifest["manifest_sha256"],
        "shared_identity_sha256": trajectory.shared_identity["identity_sha256"],
    }


def verify_stage9_phase_a_seed(
    condition: str,
    seed: int,
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if config is None:
        config = verify_stage9_config_for_execution()
    if condition not in adaptive_condition_ids(config):
        raise ValueError("Stage-9 condition is not enabled by frozen config.")
    seed_dir = _seed_dir(condition, seed)
    manifest = _load_json(seed_dir / "run_manifest.json")
    _verify_manifest_hash(manifest)
    if manifest["status"] != "complete_unscored_stage9_shared_trajectory":
        raise ValueError("Stage-9 Phase-A status mismatch.")
    scenario = manifest["scenario_identity"]
    if scenario["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 Phase-A references wrong config.")
    if scenario["condition_id"] != condition:
        raise ValueError("Stage-9 Phase-A condition mismatch.")
    if scenario["condition_spec"] != config["conditions"]["adaptive"][condition]:
        raise ValueError("Stage-9 Phase-A condition spec changed.")
    if scenario["adaptive_runner_received_boundary_metadata"] is not False:
        raise ValueError("Stage-9 boundary-contamination invariant failed.")

    verify_manifest_files(seed_dir, manifest)
    events = read_jsonl(seed_dir / "events.jsonl")
    for event in events:
        validate_event(event)
    labels = read_jsonl(seed_dir / "label_schedule.jsonl")
    detector = read_jsonl(seed_dir / "detector_observations.jsonl")
    replay = read_jsonl(seed_dir / "replay_transactions.jsonl")
    checkpoints = read_jsonl(seed_dir / "checkpoint_chain.jsonl")
    verify_checkpoint_chain(checkpoints)
    identity = _load_json(seed_dir / "shared_identity.json")
    expected = build_shared_identity(
        label_schedule_sha256=records_sha256(labels),
        detector_events_sha256=records_sha256(detector),
        replay_evidence_sha256=records_sha256(replay),
        checkpoint_chain_sha256=records_sha256(checkpoints),
    )
    if identity["shared_identity"] != expected:
        raise ValueError("Stage-9 Phase-A shared identity mismatch.")

    predictions = read_jsonl(seed_dir / "predictions.jsonl")
    if len(predictions) != 138530 or len(labels) != len(predictions):
        raise ValueError("Stage-9 Phase-A stream size mismatch.")

    cp = control_plane_for_condition(condition, config)
    for p, schedule in zip(predictions, labels):
        if int(schedule["maturity_index"]) != int(p["origin_index"]) + cp.label_latency:
            raise ValueError("Stage-9 label maturity violates condition latency.")

    for observation in detector:
        if observation["admitted"]:
            if observation.get("signal_name") != cp.detector_signal:
                raise ValueError("Stage-9 admitted detector signal type changed.")
            if observation.get("signal_value") is None:
                raise ValueError("Stage-9 admitted detector observation lacks signal.")
        elif observation.get("signal_value") is not None:
            raise ValueError("Rejected Stage-9 detector observation carries a signal value.")

    if not cp.replay_enabled:
        if any(tx["replay_row_ids"] for tx in replay):
            raise ValueError("No-replay condition contains replay rows.")

    return {
        "status": "stage9_phase_a_seed_verified_unscored",
        "condition_id": condition,
        "seed": seed,
        "run_manifest_sha256": manifest["manifest_sha256"],
        "shared_identity_sha256": expected["identity_sha256"],
        "prediction_rows": len(predictions),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", required=True)
    parser.add_argument("--seed", type=int, required=True, choices=PRIMARY_SEEDS)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (
        verify_stage9_phase_a_seed(args.condition, args.seed)
        if args.verify_only
        else execute_stage9_phase_a_seed(args.condition, args.seed)
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
