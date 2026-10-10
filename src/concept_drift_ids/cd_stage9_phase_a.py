from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from concept_drift_ids.cd_control_plane import write_json_new
from concept_drift_ids.cd_evidence import (
    build_run_manifest,
    read_jsonl,
    validate_event,
    verify_checkpoint_chain,
    verify_manifest_files,
)
from concept_drift_ids.cd_primary_adapter import build_primary_input_bundle
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_shared_runner import freeze_shared_trajectory
from concept_drift_ids.cd_stage9_config import (
    PRIMARY_SEEDS,
    STAGE9_OUTPUT_ROOT,
    STAGE9_RUN_ID,
    _git_output,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_control_plane import (
    Stage9ControlPlaneConfig,
    Stage9SharedControlPlaneRunner,
    verify_stage9_shared_trajectory,
)
from concept_drift_ids.scenario_manifest import sha256_file


ADAPTIVE_CONDITIONS = (
    "A_BASELINE",
    "A_LATENCY_0",
    "A_LATENCY_10000",
    "A_PAGE_HINKLEY",
    "A_ADWIN_BRIER",
    "A_NO_REPLAY",
)


def condition_control_plane_config(
    condition_id: str,
    config: Mapping[str, Any],
) -> Stage9ControlPlaneConfig:
    if condition_id not in ADAPTIVE_CONDITIONS:
        raise ValueError(f"Not a Stage-9 adaptive condition: {condition_id}")
    condition = config["conditions"][condition_id]
    replay = str(condition["replay"])
    detector = str(condition["detector"])
    latency = int(condition["label_latency"])
    return Stage9ControlPlaneConfig(
        label_latency=latency,
        replay_mode=replay,
        detector_kind=detector,
    )


def _condition_root(condition_id: str) -> Path:
    return STAGE9_OUTPUT_ROOT / "adaptive" / condition_id


def _seed_dir(condition_id: str, seed: int) -> Path:
    return _condition_root(condition_id) / "phase_a_shared_control_plane" / f"seed-{seed}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _child_checkpoint_descriptors(seed_dir: Path) -> dict[str, dict[str, str]]:
    checkpoint_dir = seed_dir / "checkpoints"
    if not checkpoint_dir.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    for index, path in enumerate(sorted(checkpoint_dir.glob("*.pt")), start=1):
        out[f"child_checkpoint_{index:04d}"] = {
            "path": path.relative_to(seed_dir).as_posix(),
            "sha256": sha256_file(path),
        }
    return out


def execute_stage9_phase_a_seed(condition_id: str, seed: int) -> dict[str, Any]:
    if condition_id not in ADAPTIVE_CONDITIONS:
        raise ValueError(f"Unsupported adaptive condition: {condition_id}")
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")

    config = verify_stage9_config_for_execution()
    condition = config["conditions"][condition_id]
    if condition_id == "A_BASELINE" and not bool(condition["required"]):
        raise RuntimeError(
            "A_BASELINE is prohibited when the frozen Stage-9 runtime is materially identical "
            "to Stage 8; avoid unnecessary post-primary reruns."
        )

    runtime = configure_torch_primary_runtime()
    cp_config = condition_control_plane_config(condition_id, config)
    seed_dir = _seed_dir(condition_id, seed)
    if seed_dir.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 Phase-A output: {seed_dir}")
    seed_dir.mkdir(parents=True, exist_ok=False)

    run_id = f"{STAGE9_RUN_ID}-{condition_id}-phase-a-seed-{seed}"
    write_json_new(
        seed_dir / "attempt.json",
        {
            "run_id": run_id,
            "condition_id": condition_id,
            "seed": seed,
            "git_commit": _git_output("rev-parse", "HEAD"),
            "stage9_config_manifest_sha256": config["manifest_sha256"],
            "stage8_parent_evidence_commit": config["parent_stage8"]["evidence_commit"],
            "boundary_metadata_supplied_to_runner": False,
            "symbolic_arms_executed": False,
            "stage9_outcome_access_started": True,
        },
    )

    try:
        bundle = build_primary_input_bundle(seed)
        input_identity_path = seed_dir / "input_identity.json"
        input_identity_sha256 = write_json_new(
            input_identity_path,
            {
                **bundle.audit_identity,
                "stage9_condition_id": condition_id,
                "stage9_config_manifest_sha256": config["manifest_sha256"],
            },
        )

        runner = Stage9SharedControlPlaneRunner(
            seed=seed,
            initial_model=bundle.model,
            initial_checkpoint_sha256=bundle.initial_checkpoint_sha256,
            monitor_threshold=bundle.monitor_threshold,
            anchor_rows=bundle.anchor_rows,
            checkpoint_dir=seed_dir / "checkpoints",
            run_id=run_id,
            git_commit=_git_output("rev-parse", "HEAD"),
            condition_id=condition_id,
            config=cp_config,
        )
        trajectory = runner.run(bundle.stream_rows)
        verify_stage9_shared_trajectory(
            trajectory,
            config=cp_config,
            condition_id=condition_id,
        )

        files = freeze_shared_trajectory(seed_dir, trajectory)
        files["input_identity"] = {
            "path": input_identity_path.name,
            "sha256": input_identity_sha256,
        }
        files.update(_child_checkpoint_descriptors(seed_dir))

        manifest = build_run_manifest(
            run_id=run_id,
            seed=seed,
            git_commit=_git_output("rev-parse", "HEAD"),
            protocol_hashes={
                config["protocol"]["path"]: config["protocol"]["sha256"],
                config["implementation_freeze"]["path"]: config[
                    "implementation_freeze"
                ]["sha256"],
            },
            runtime=runtime,
            scenario_identity={
                "stage9_config_manifest_sha256": config["manifest_sha256"],
                "stage8_parent_evidence_commit": config["parent_stage8"][
                    "evidence_commit"
                ],
                "condition_id": condition_id,
                "condition": condition,
                "scenario": config["scenario"],
                "input_identity": bundle.audit_identity,
                "adaptive_runner_received_boundary_metadata": False,
            },
            initial_checkpoint_sha256=bundle.initial_checkpoint_sha256,
            preprocessing_sha256=bundle.preprocessing_state_hash,
            files=files,
            status="complete_unscored_stage9_shared_trajectory",
        )
        write_json_new(seed_dir / "run_manifest.json", manifest)
        verify_manifest_files(seed_dir, manifest)
        verified = verify_stage9_phase_a_seed(condition_id, seed)
    except Exception as exc:
        failure = seed_dir / "failure.json"
        if not failure.exists():
            write_json_new(
                failure,
                {
                    "condition_id": condition_id,
                    "seed": seed,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "boundary_metadata_supplied_to_runner": False,
                    "symbolic_arms_executed": False,
                },
            )
        raise

    return {
        "status": "stage9_phase_a_seed_complete_unscored",
        "condition_id": condition_id,
        "seed": seed,
        "run_manifest_sha256": verified["run_manifest_sha256"],
        "shared_identity_sha256": verified["shared_identity_sha256"],
    }


def verify_stage9_phase_a_seed(
    condition_id: str,
    seed: int,
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if condition_id not in ADAPTIVE_CONDITIONS:
        raise ValueError(f"Unsupported adaptive condition: {condition_id}")
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")
    if config is None:
        config = verify_stage9_config_for_execution(require_clean=False)
    cp_config = condition_control_plane_config(condition_id, config)

    seed_dir = _seed_dir(condition_id, seed)
    manifest_path = seed_dir / "run_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing Stage-9 Phase-A manifest: {manifest_path}")
    manifest = _read_json(manifest_path)
    if manifest["status"] != "complete_unscored_stage9_shared_trajectory":
        raise ValueError("Stage-9 Phase-A status is not complete/unscored.")
    if int(manifest["seed"]) != seed:
        raise ValueError("Stage-9 Phase-A seed mismatch.")

    scenario = manifest["scenario_identity"]
    if scenario["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 Phase-A references wrong config.")
    if scenario["stage8_parent_evidence_commit"] != config["parent_stage8"][
        "evidence_commit"
    ]:
        raise ValueError("Stage-9 Phase-A parent Stage-8 evidence changed.")
    if scenario["condition_id"] != condition_id:
        raise ValueError("Stage-9 Phase-A condition identity mismatch.")
    if scenario["condition"] != config["conditions"][condition_id]:
        raise ValueError("Stage-9 Phase-A condition definition changed.")
    if scenario.get("adaptive_runner_received_boundary_metadata") is not False:
        raise ValueError("Boundary metadata contamination flag is not false.")

    verify_manifest_files(seed_dir, manifest)
    events = read_jsonl(seed_dir / "events.jsonl")
    for event in events:
        validate_event(event)
    predictions = read_jsonl(seed_dir / "predictions.jsonl")
    labels = read_jsonl(seed_dir / "label_schedule.jsonl")
    detector = read_jsonl(seed_dir / "detector_observations.jsonl")
    replay = read_jsonl(seed_dir / "replay_transactions.jsonl")
    checkpoints = read_jsonl(seed_dir / "checkpoint_chain.jsonl")
    verify_checkpoint_chain(checkpoints)

    from concept_drift_ids.cd_shared_runner import SharedTrajectory

    identity = _read_json(seed_dir / "shared_identity.json")
    trajectory = SharedTrajectory(
        seed=seed,
        config_sha256=str(identity["config_sha256"]),
        predictions=tuple(predictions),
        label_schedule=tuple(labels),
        detector_observations=tuple(detector),
        events=tuple(events),
        replay_transactions=tuple(replay),
        checkpoint_chain=tuple(checkpoints),
        shared_identity=identity["shared_identity"],
        final_checkpoint_sha256=str(identity["final_checkpoint_sha256"]),
        final_state_sha256=str(identity["final_state_sha256"]),
        pending_labels=int(identity["pending_labels"]),
        pending_neural_transaction=identity["pending_neural_transaction"],
    )
    verify_stage9_shared_trajectory(
        trajectory,
        config=cp_config,
        condition_id=condition_id,
    )
    if len(predictions) != int(config["scenario"]["stream_rows"]):
        raise ValueError("Stage-9 Phase-A prediction row count mismatch.")

    return {
        "status": "stage9_phase_a_seed_verified_unscored",
        "condition_id": condition_id,
        "seed": seed,
        "run_manifest_sha256": manifest["manifest_sha256"],
        "shared_identity_sha256": identity["shared_identity"]["identity_sha256"],
        "prediction_rows": len(predictions),
        "outcome_metrics_exposed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute or verify Stage-9 adaptive Phase A.")
    parser.add_argument("--condition", required=True, choices=ADAPTIVE_CONDITIONS)
    parser.add_argument("--seed", required=True, type=int, choices=PRIMARY_SEEDS)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.verify_only:
        result = verify_stage9_phase_a_seed(args.condition, args.seed)
    else:
        result = execute_stage9_phase_a_seed(args.condition, args.seed)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
