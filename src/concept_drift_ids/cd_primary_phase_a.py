from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from concept_drift_ids.cd_control_plane import (
    canonical_sha256,
    write_json_new,
)
from concept_drift_ids.cd_evidence import (
    build_run_manifest,
    build_shared_identity,
    read_jsonl,
    records_sha256,
    validate_event,
    verify_checkpoint_chain,
    verify_manifest_files,
)
from concept_drift_ids.cd_primary_config import (
    PRIMARY_OUTPUT_ROOT,
    PRIMARY_RUN_ID,
    PRIMARY_SEEDS,
    _git_output,
    verify_primary_run_config_for_execution,
)
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_shared_runner import (
    ControlPlaneConfig,
    SharedControlPlaneRunner,
    freeze_shared_trajectory,
    verify_primary_control_plane_configuration,
    verify_shared_trajectory,
)
from concept_drift_ids.scenario_manifest import sha256_file


def _seed_dir(seed: int) -> Path:
    return PRIMARY_OUTPUT_ROOT / "phase_a_shared_control_plane" / f"seed-{seed}"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_run_manifest_hash(manifest: dict[str, Any]) -> None:
    body = dict(manifest)
    body.pop("payload_sha256", None)
    stored = body.pop("manifest_sha256", None)
    if stored != canonical_sha256(body):
        raise ValueError("Phase-A run manifest canonical hash mismatch.")


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


def execute_phase_a_seed(seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported primary seed: {seed}")

    config = verify_primary_run_config_for_execution()
    runtime = configure_torch_primary_runtime()
    seed_dir = _seed_dir(seed)
    if seed_dir.exists():
        raise FileExistsError(
            f"Refusing to reuse existing primary seed output: {seed_dir}"
        )

    # Import only after the tracked/clean frozen-config gate has passed.
    from concept_drift_ids.cd_primary_adapter import build_primary_input_bundle

    bundle = build_primary_input_bundle(seed)
    verify_primary_control_plane_configuration(
        seed=seed,
        monitor_threshold=bundle.monitor_threshold,
        anchor_row_count=len(bundle.anchor_rows),
        config=ControlPlaneConfig(),
    )

    seed_dir.mkdir(parents=True, exist_ok=False)
    input_identity_path = seed_dir / "input_identity.json"
    input_identity_sha256 = write_json_new(
        input_identity_path,
        bundle.audit_identity,
    )

    checkpoint_dir = seed_dir / "checkpoints"
    runner = SharedControlPlaneRunner(
        seed=seed,
        initial_model=bundle.model,
        initial_checkpoint_sha256=bundle.initial_checkpoint_sha256,
        monitor_threshold=bundle.monitor_threshold,
        anchor_rows=bundle.anchor_rows,
        checkpoint_dir=checkpoint_dir,
        run_id=f"{PRIMARY_RUN_ID}-phase-a-seed-{seed}",
        git_commit=_git_output("rev-parse", "HEAD"),
        config=ControlPlaneConfig(),
    )
    trajectory = runner.run(bundle.stream_rows)
    verify_shared_trajectory(
        trajectory,
        label_latency=ControlPlaneConfig().label_latency,
    )

    files = freeze_shared_trajectory(seed_dir, trajectory)
    files["input_identity"] = {
        "path": input_identity_path.name,
        "sha256": input_identity_sha256,
    }
    files.update(_child_checkpoint_descriptors(seed_dir))

    manifest = build_run_manifest(
        run_id=f"{PRIMARY_RUN_ID}-phase-a-seed-{seed}",
        seed=seed,
        git_commit=_git_output("rev-parse", "HEAD"),
        protocol_hashes=config["protocol_hashes"],
        runtime=runtime,
        scenario_identity={
            "primary_config_manifest_sha256": config["manifest_sha256"],
            "scientific_source_tree_sha256": config[
                "scientific_source_tree_sha256"
            ],
            "scenario": config["scenario"],
            "input_identity": bundle.audit_identity,
            "adaptive_runner_received_boundary_metadata": False,
        },
        initial_checkpoint_sha256=bundle.initial_checkpoint_sha256,
        preprocessing_sha256=bundle.preprocessing_state_hash,
        files=files,
        status="complete_unscored_shared_trajectory",
    )
    run_manifest_path = seed_dir / "run_manifest.json"
    write_json_new(run_manifest_path, manifest)
    verify_manifest_files(seed_dir, manifest)
    verify_phase_a_seed(seed)

    return {
        "status": "phase_a_seed_complete_unscored",
        "seed": seed,
        "output_dir": seed_dir.as_posix(),
        "run_manifest_sha256": manifest["manifest_sha256"],
        "shared_identity_sha256": trajectory.shared_identity[
            "identity_sha256"
        ],
        "checkpoint_count": len(trajectory.checkpoint_chain),
        "drift_event_count": sum(
            int(
                event.get("event_type") == "drift_event"
                and event.get("status") == "confirmed"
            )
            for event in trajectory.events
        ),
        "pending_labels": trajectory.pending_labels,
        "pending_neural_transaction": (
            trajectory.pending_neural_transaction is not None
        ),
        "primary_boundary_scored": False,
        "symbolic_arms_executed": False,
    }


def verify_phase_a_seed(seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported primary seed: {seed}")
    config = verify_primary_run_config_for_execution()
    seed_dir = _seed_dir(seed)
    manifest_path = seed_dir / "run_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing Phase-A run manifest: {manifest_path}")
    manifest = _load_json(manifest_path)
    _verify_run_manifest_hash(manifest)
    if int(manifest["seed"]) != seed:
        raise ValueError("Phase-A manifest seed mismatch.")
    if manifest["status"] != "complete_unscored_shared_trajectory":
        raise ValueError("Phase-A run status is not complete/unscored.")
    if (
        manifest["scenario_identity"]["primary_config_manifest_sha256"]
        != config["manifest_sha256"]
    ):
        raise ValueError("Phase-A run references the wrong primary config.")
    if manifest["scenario_identity"].get(
        "adaptive_runner_received_boundary_metadata"
    ) is not False:
        raise ValueError("Boundary metadata contamination flag is not false.")

    verify_manifest_files(seed_dir, manifest)
    events = read_jsonl(seed_dir / "events.jsonl")
    for event in events:
        validate_event(event)
    label_schedule = read_jsonl(seed_dir / "label_schedule.jsonl")
    detector = read_jsonl(seed_dir / "detector_observations.jsonl")
    replay = read_jsonl(seed_dir / "replay_transactions.jsonl")
    checkpoints = read_jsonl(seed_dir / "checkpoint_chain.jsonl")
    verify_checkpoint_chain(checkpoints)

    identity_file = _load_json(seed_dir / "shared_identity.json")
    expected_identity = build_shared_identity(
        label_schedule_sha256=records_sha256(label_schedule),
        detector_events_sha256=records_sha256(detector),
        replay_evidence_sha256=records_sha256(replay),
        checkpoint_chain_sha256=records_sha256(checkpoints),
    )
    if identity_file["shared_identity"] != expected_identity:
        raise ValueError("Frozen Phase-A shared identity mismatch.")

    predictions = read_jsonl(seed_dir / "predictions.jsonl")
    if len(predictions) != int(config["scenario"]["stream_rows"]):
        raise ValueError("Phase-A prediction row count mismatch.")
    if len(label_schedule) != len(predictions):
        raise ValueError("Phase-A label schedule/prediction count mismatch.")

    return {
        "status": "phase_a_seed_verified_unscored",
        "seed": seed,
        "run_manifest_sha256": manifest["manifest_sha256"],
        "shared_identity_sha256": expected_identity["identity_sha256"],
        "prediction_rows": len(predictions),
        "checkpoint_count": len(checkpoints),
        "primary_boundary_scored": False,
        "symbolic_arms_executed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Execute or verify one primary Phase-A shared control-plane seed. "
            "No boundary scoring or symbolic arm evaluation occurs here."
        )
    )
    parser.add_argument("--seed", type=int, required=True, choices=PRIMARY_SEEDS)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify an existing write-once Phase-A seed artifact.",
    )
    args = parser.parse_args()

    result = (
        verify_phase_a_seed(args.seed)
        if args.verify_only
        else execute_phase_a_seed(args.seed)
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
