from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch

from concept_drift_ids.cd_analysis import summarize_symbolic_maintenance
from concept_drift_ids.cd_control_plane import (
    canonical_sha256,
    state_dict_sha256,
    write_json_new,
)
from concept_drift_ids.cd_evidence import (
    read_jsonl,
    write_jsonl_new,
)
from concept_drift_ids.cd_primary_adapter import (
    load_accepted_system_a_model,
    load_primary_stream,
)
from concept_drift_ids.cd_primary_config import (
    PRIMARY_OUTPUT_ROOT,
    PRIMARY_RUN_ID,
    PRIMARY_SEEDS,
    _git_output,
    verify_primary_run_config_for_execution,
)
from concept_drift_ids.cd_primary_phase_a import verify_phase_a_seed
from concept_drift_ids.cd_r0_lifecycle import migrate_accepted_r0_v2_state
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_symbolic_arms import SymbolicOperatorConfig
from concept_drift_ids.cd_symbolic_lifecycle import (
    RuleBaseState,
    rule_base_state_from_dict,
    verify_lifecycle_state,
)
from concept_drift_ids.cd_symbolic_runner import (
    SharedSymbolicRow,
    SymbolicArmTrajectory,
    frozen_c_arm,
    run_drift_symbolic_arm,
    run_periodic_symbolic_arm,
    verify_symbolic_arm_control_plane_isolation,
)
from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing
from concept_drift_ids.neural import BinaryMLP
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.system_a import SYSTEM_A_CONFIG


ARM_NAMES = ("c_frozen_symbolic", "d_drift", "d_periodic")


def _phase_a_dir(seed: int) -> Path:
    return (
        PRIMARY_OUTPUT_ROOT
        / "phase_a_shared_control_plane"
        / f"seed-{seed}"
    )


def _phase_b_dir(seed: int) -> Path:
    return (
        PRIMARY_OUTPUT_ROOT
        / "phase_b_symbolic_arms"
        / f"seed-{seed}"
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_json_payload(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    stored = payload.pop("payload_sha256", None)
    if stored is not None and canonical_sha256(payload) != stored:
        raise ValueError(f"JSON payload hash mismatch: {path}")
    return payload


def _new_model() -> BinaryMLP:
    return BinaryMLP(
        input_features=int(SYSTEM_A_CONFIG["input_features"]),
        hidden_layers=tuple(SYSTEM_A_CONFIG["hidden_layers"]),
        dropout=float(SYSTEM_A_CONFIG["dropout"]),
    )


def _build_model_resolver(
    seed: int,
    *,
    phase_a_dir: Path,
    checkpoint_chain: Sequence[Mapping[str, Any]],
) -> Callable[[str], BinaryMLP]:
    preprocessing = load_frozen_preprocessing()
    initial_model, initial_hash = load_accepted_system_a_model(
        seed,
        preprocessing=preprocessing,
    )
    chain_by_file = {
        str(record["checkpoint_file_sha256"]): record
        for record in checkpoint_chain
    }
    if initial_hash not in chain_by_file:
        raise ValueError("Initial System-A checkpoint absent from Phase-A chain.")

    child_paths: dict[str, Path] = {}
    checkpoint_dir = phase_a_dir / "checkpoints"
    if checkpoint_dir.exists():
        for path in sorted(checkpoint_dir.glob("*.pt")):
            digest = sha256_file(path)
            if digest in child_paths:
                raise ValueError("Duplicate child checkpoint file identity.")
            child_paths[digest] = path

    cache: dict[str, BinaryMLP] = {initial_hash: initial_model}

    def resolve(checkpoint_sha256: str) -> BinaryMLP:
        checkpoint_sha256 = str(checkpoint_sha256)
        if checkpoint_sha256 in cache:
            return cache[checkpoint_sha256]
        if checkpoint_sha256 not in chain_by_file:
            raise ValueError("Requested model is absent from checkpoint chain.")
        path = child_paths.get(checkpoint_sha256)
        if path is None:
            raise FileNotFoundError(
                "Checkpoint chain references a missing child checkpoint file."
            )
        if sha256_file(path) != checkpoint_sha256:
            raise ValueError("Child checkpoint raw file hash mismatch.")
        payload = torch.load(path, map_location="cpu", weights_only=False)
        model = _new_model()
        model.load_state_dict(payload["state_dict"])
        model.cpu().eval()
        expected_state = str(
            chain_by_file[checkpoint_sha256]["child_state_sha256"]
        )
        if str(payload["state_sha256"]) != expected_state:
            raise ValueError("Child checkpoint embedded state hash mismatch.")
        if state_dict_sha256(model) != expected_state:
            raise ValueError("Child checkpoint reconstructed state mismatch.")
        metadata = payload["metadata"]
        if str(metadata["run_id"]) != (
            f"{PRIMARY_RUN_ID}-phase-a-seed-{seed}"
        ):
            raise ValueError("Child checkpoint run identity mismatch.")
        cache[checkpoint_sha256] = model
        return model

    return resolve


def _shared_symbolic_rows(
    *,
    stream_rows: Sequence[Any],
    predictions: Sequence[Mapping[str, Any]],
) -> tuple[SharedSymbolicRow, ...]:
    if len(stream_rows) != len(predictions):
        raise ValueError("Primary stream and Phase-A predictions differ in size.")
    rows: list[SharedSymbolicRow] = []
    for index, (stream, prediction) in enumerate(
        zip(stream_rows, predictions)
    ):
        if stream.row_id != prediction["row_id"]:
            raise ValueError("Phase-B row identity differs from Phase A.")
        if int(prediction["origin_index"]) != index:
            raise ValueError("Phase-A prediction origin order changed.")
        rows.append(
            SharedSymbolicRow(
                row_id=stream.row_id,
                origin_index=index,
                maturity_index=int(prediction["maturity_index"]),
                features=np.asarray(stream.features, dtype=np.float32),
                true_label=int(stream.label),
                neural_probability=float(
                    prediction["neural_probability"]
                ),
                neural_checkpoint_sha256=str(
                    prediction["checkpoint_sha256"]
                ),
            )
        )
    return tuple(rows)


def _maintenance_payload(record: Any) -> dict[str, Any]:
    transaction = record.lifecycle
    lifecycle = transaction.lifecycle if transaction is not None else None
    return {
        "arm": record.arm,
        "opportunity_id": int(record.opportunity_id),
        "opportunity_clock": int(record.opportunity_clock),
        "status": str(record.status),
        "neural_checkpoint_sha256": record.neural_checkpoint_sha256,
        "generation_evidence_id": record.generation_evidence_id,
        "generation_row_ids": list(record.generation_row_ids),
        "validation_row_ids": list(record.validation_row_ids),
        "validation_completion_clock": record.validation_completion_clock,
        "symbolic_publication_effective_index": (
            record.symbolic_publication_effective_index
        ),
        "parent_rule_base_version_id": (
            record.parent_rule_base_version_id
        ),
        "result_rule_base_version_id": (
            record.result_rule_base_version_id
        ),
        "parent_rule_base_sha256": record.parent_rule_base_sha256,
        "result_rule_base_sha256": record.result_rule_base_sha256,
        "history_sha256": record.history_sha256,
        "candidate_count": int(record.candidate_count),
        "shap_seconds": float(record.shap_seconds),
        "surrogate_seconds": float(record.surrogate_seconds),
        "lifecycle_seconds": float(record.lifecycle_seconds),
        "validation_wait_rows": record.validation_wait_rows,
        "generation_payload": (
            dict(record.generation_payload)
            if record.generation_payload is not None
            else None
        ),
        "lifecycle": (
            {
                "transaction_status": transaction.status,
                "published": bool(lifecycle.published),
                "maintenance_status": lifecycle.maintenance_status,
                "result_rule_base_version_id": (
                    lifecycle.state.rule_base_version_id
                ),
                "result_rule_base_sha256": (
                    lifecycle.state.canonical_sha256
                ),
                "result_history_sha256": lifecycle.state.history_sha256,
                "decisions": list(lifecycle.decisions),
                "staleness_snapshot": list(
                    lifecycle.staleness_snapshot
                ),
                "candidate_evidence": list(
                    lifecycle.candidate_evidence
                ),
            }
            if lifecycle is not None
            else None
        ),
    }


def _freeze_arm(
    arm_dir: Path,
    trajectory: SymbolicArmTrajectory,
) -> dict[str, Any]:
    if arm_dir.exists():
        raise FileExistsError(f"Refusing to overwrite symbolic arm: {arm_dir}")
    arm_dir.mkdir(parents=True, exist_ok=False)

    initial_path = arm_dir / "initial_state.json"
    initial_sha = write_json_new(
        initial_path,
        trajectory.initial_state.to_dict(),
    )
    final_path = arm_dir / "final_state.json"
    final_sha = write_json_new(
        final_path,
        trajectory.final_state.to_dict(),
    )
    maintenance_path = arm_dir / "maintenance.jsonl"
    maintenance_sha = write_jsonl_new(
        maintenance_path,
        [_maintenance_payload(item) for item in trajectory.maintenance],
        validate=False,
    )

    publications: list[dict[str, Any]] = []
    version_files: dict[str, dict[str, str]] = {}
    versions_dir = arm_dir / "versions"
    for ordinal, (effective_index, state) in enumerate(
        sorted(trajectory.publications, key=lambda item: item[0]),
        start=1,
    ):
        verify_lifecycle_state(state)
        path = versions_dir / (
            f"{ordinal:04d}-{state.rule_base_version_id}.json"
        )
        digest = write_json_new(
            path,
            {
                "effective_index": int(effective_index),
                "state": state.to_dict(),
            },
        )
        key = f"version_{ordinal:04d}"
        version_files[key] = {
            "path": path.relative_to(arm_dir).as_posix(),
            "sha256": digest,
        }
        publications.append(
            {
                "effective_index": int(effective_index),
                "rule_base_version_id": state.rule_base_version_id,
                "canonical_sha256": state.canonical_sha256,
                "history_sha256": state.history_sha256,
                "file_key": key,
            }
        )

    files: dict[str, dict[str, str]] = {
        "initial_state": {
            "path": initial_path.name,
            "sha256": initial_sha,
        },
        "final_state": {
            "path": final_path.name,
            "sha256": final_sha,
        },
        "maintenance": {
            "path": maintenance_path.name,
            "sha256": maintenance_sha,
        },
        **version_files,
    }
    manifest = {
        "schema_version": 1,
        "seed": trajectory.seed,
        "arm": trajectory.arm,
        "operator_config_sha256": trajectory.operator_config_sha256,
        "shared_identity_sha256": trajectory.shared_identity_sha256,
        "initial_rule_base_version_id": (
            trajectory.initial_state.rule_base_version_id
        ),
        "initial_rule_base_sha256": (
            trajectory.initial_state.canonical_sha256
        ),
        "final_rule_base_version_id": (
            trajectory.final_state.rule_base_version_id
        ),
        "final_rule_base_sha256": trajectory.final_state.canonical_sha256,
        "final_history_sha256": trajectory.final_state.history_sha256,
        "publications": publications,
        "maintenance_summary": summarize_symbolic_maintenance(
            trajectory.maintenance
        ),
        "files": files,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    manifest_path = arm_dir / "arm_manifest.json"
    manifest_file_sha = write_json_new(manifest_path, manifest)
    return {
        "path": manifest_path.relative_to(_phase_b_dir(trajectory.seed)).as_posix(),
        "sha256": manifest_file_sha,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def _verify_arm_files(
    arm_dir: Path,
    manifest: Mapping[str, Any],
) -> None:
    for descriptor in manifest["files"].values():
        path = arm_dir / str(descriptor["path"])
        if not path.is_file():
            raise FileNotFoundError(f"Missing symbolic arm file: {path}")
        if sha256_file(path) != str(descriptor["sha256"]):
            raise ValueError(f"Symbolic arm file hash mismatch: {path}")


def load_frozen_arm_trajectory(
    seed: int,
    arm: str,
) -> SymbolicArmTrajectory:
    if arm not in ARM_NAMES:
        raise ValueError(f"Unknown frozen symbolic arm: {arm}")
    arm_dir = _phase_b_dir(seed) / arm
    manifest = _verify_json_payload(arm_dir / "arm_manifest.json")
    stored_manifest_sha = manifest.pop("manifest_sha256", None)
    if stored_manifest_sha != canonical_sha256(manifest):
        raise ValueError("Symbolic arm manifest canonical hash mismatch.")
    _verify_arm_files(arm_dir, manifest)

    initial_payload = _verify_json_payload(
        arm_dir / manifest["files"]["initial_state"]["path"]
    )
    final_payload = _verify_json_payload(
        arm_dir / manifest["files"]["final_state"]["path"]
    )
    initial = rule_base_state_from_dict(initial_payload)
    final = rule_base_state_from_dict(final_payload)
    if initial.seed != seed or final.seed != seed:
        raise ValueError("Symbolic arm state seed mismatch.")
    if manifest["seed"] != seed or manifest["arm"] != arm:
        raise ValueError("Symbolic arm manifest identity mismatch.")
    if (
        manifest["initial_rule_base_version_id"]
        != initial.rule_base_version_id
        or manifest["initial_rule_base_sha256"]
        != initial.canonical_sha256
    ):
        raise ValueError("Symbolic arm initial-state identity mismatch.")
    if (
        manifest["final_rule_base_version_id"]
        != final.rule_base_version_id
        or manifest["final_rule_base_sha256"]
        != final.canonical_sha256
        or manifest["final_history_sha256"] != final.history_sha256
    ):
        raise ValueError("Symbolic arm final-state identity mismatch.")

    publications: list[tuple[int, RuleBaseState]] = []
    previous_state = initial
    previous_effective = -1
    for item in manifest["publications"]:
        descriptor = manifest["files"][item["file_key"]]
        payload = _verify_json_payload(arm_dir / descriptor["path"])
        state = rule_base_state_from_dict(payload["state"])
        effective_index = int(payload["effective_index"])
        if effective_index != int(item["effective_index"]):
            raise ValueError("Symbolic publication effective-index mismatch.")
        if effective_index <= previous_effective:
            raise ValueError("Symbolic publication clocks are not increasing.")
        if state.rule_base_version_id != item["rule_base_version_id"]:
            raise ValueError("Symbolic publication version ID mismatch.")
        if state.canonical_sha256 != item["canonical_sha256"]:
            raise ValueError("Symbolic publication state hash mismatch.")
        if state.history_sha256 != item["history_sha256"]:
            raise ValueError("Symbolic publication history hash mismatch.")
        if state.parent_version_id != previous_state.rule_base_version_id:
            raise ValueError("Symbolic publication parent version mismatch.")
        if state.parent_version_sha256 != previous_state.canonical_sha256:
            raise ValueError("Symbolic publication parent hash mismatch.")
        if state.version_number != previous_state.version_number + 1:
            raise ValueError("Symbolic publication version sequence mismatch.")
        publications.append((effective_index, state))
        previous_state = state
        previous_effective = effective_index

    if publications:
        last_published = publications[-1][1]
        if (
            final.rule_base_version_id
            != last_published.rule_base_version_id
            or final.canonical_sha256
            != last_published.canonical_sha256
        ):
            raise ValueError(
                "Final inference state differs from last symbolic publication."
            )
    elif final.canonical_sha256 != initial.canonical_sha256:
        raise ValueError(
            "Final inference state changed without a symbolic publication."
        )

    return SymbolicArmTrajectory(
        seed=seed,
        arm=arm,
        operator_config_sha256=str(
            manifest["operator_config_sha256"]
        ),
        shared_identity_sha256=str(
            manifest["shared_identity_sha256"]
        ),
        initial_state=initial,
        final_state=final,
        maintenance=(),
        publications=tuple(publications),
    )


def verify_phase_b_seed(seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported primary seed: {seed}")
    config = verify_primary_run_config_for_execution()
    phase_b_dir = _phase_b_dir(seed)
    manifest_path = phase_b_dir / "phase_b_manifest.json"
    manifest = _verify_json_payload(manifest_path)
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError("Phase-B manifest canonical hash mismatch.")
    if int(manifest["seed"]) != seed:
        raise ValueError("Phase-B seed mismatch.")
    if manifest["primary_config_manifest_sha256"] != config[
        "manifest_sha256"
    ]:
        raise ValueError("Phase-B references the wrong primary config.")

    for arm in ARM_NAMES:
        descriptor = manifest["arms"].get(arm)
        if descriptor is None:
            raise ValueError(f"Phase-B manifest lacks arm descriptor: {arm}")
        arm_manifest_path = phase_b_dir / str(descriptor["path"])
        if sha256_file(arm_manifest_path) != str(descriptor["sha256"]):
            raise ValueError("Phase-B arm-manifest file hash mismatch.")
        arm_manifest = _verify_json_payload(arm_manifest_path)
        if arm_manifest.get("manifest_sha256") != descriptor[
            "manifest_sha256"
        ]:
            raise ValueError("Phase-B arm-manifest identity mismatch.")

    trajectories = tuple(
        load_frozen_arm_trajectory(seed, arm) for arm in ARM_NAMES
    )
    isolation = verify_symbolic_arm_control_plane_isolation(trajectories)
    if isolation != manifest["arm_isolation_sha256"]:
        raise ValueError("Phase-B arm-isolation identity mismatch.")
    return {
        "status": "phase_b_seed_verified_unscored",
        "seed": seed,
        "phase_b_manifest_sha256": stored,
        "arm_isolation_sha256": isolation,
        "primary_boundary_scored": False,
    }


def execute_phase_b_seed(seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported primary seed: {seed}")
    config = verify_primary_run_config_for_execution()
    configure_torch_primary_runtime()

    # Freeze/verify all shared trajectories before any symbolic treatment.
    phase_a_verified = {
        other: verify_phase_a_seed(other) for other in PRIMARY_SEEDS
    }
    shared_identities = {
        other: item["shared_identity_sha256"]
        for other, item in phase_a_verified.items()
    }

    output_dir = _phase_b_dir(seed)
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to reuse existing Phase-B output: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=False)

    phase_a_dir = _phase_a_dir(seed)
    identity = _verify_json_payload(
        phase_a_dir / "shared_identity.json"
    )["shared_identity"]
    operator = SymbolicOperatorConfig()
    write_json_new(
        output_dir / "attempt.json",
        {
            "run_id": f"{PRIMARY_RUN_ID}-phase-b-seed-{seed}",
            "seed": seed,
            "git_commit": _git_output("rev-parse", "HEAD"),
            "primary_config_manifest_sha256": config["manifest_sha256"],
            "shared_identity_sha256": identity["identity_sha256"],
            "operator_config_sha256": operator.sha256(),
            "primary_boundary_scored": False,
        },
    )

    try:
        predictions = read_jsonl(phase_a_dir / "predictions.jsonl")
        events = read_jsonl(phase_a_dir / "events.jsonl")
        replay = read_jsonl(phase_a_dir / "replay_transactions.jsonl")
        checkpoint_chain = read_jsonl(
            phase_a_dir / "checkpoint_chain.jsonl"
        )
        if identity["identity_sha256"] != shared_identities[seed]:
            raise ValueError(
                "Phase-A shared identity changed before Phase B."
            )

        preprocessing = load_frozen_preprocessing()
        stream_rows = load_primary_stream(preprocessing=preprocessing)
        symbolic_rows = _shared_symbolic_rows(
            stream_rows=stream_rows,
            predictions=predictions,
        )
        initial_checkpoint_sha256 = str(
            checkpoint_chain[0]["checkpoint_file_sha256"]
        )
        initial_state = migrate_accepted_r0_v2_state(
            seed,
            neural_checkpoint_sha256=initial_checkpoint_sha256,
        )
        model_resolver = _build_model_resolver(
            seed,
            phase_a_dir=phase_a_dir,
            checkpoint_chain=checkpoint_chain,
        )
        raw_affine = {
            feature: (
                float(preprocessing.means[index]),
                float(preprocessing.scales[index]),
            )
            for index, feature in enumerate(
                preprocessing.feature_columns
            )
        }

        c_arm = frozen_c_arm(
            seed=seed,
            initial_state=initial_state,
            shared_identity_sha256=identity["identity_sha256"],
            operator_config=operator,
        )
        d_drift = run_drift_symbolic_arm(
            seed=seed,
            initial_state=initial_state,
            shared_identity_sha256=identity["identity_sha256"],
            shared_predictions=predictions,
            shared_events=events,
            replay_transactions=replay,
            checkpoint_chain=checkpoint_chain,
            rows=symbolic_rows,
            feature_names=preprocessing.feature_columns,
            model_resolver=model_resolver,
            raw_affine=raw_affine,
            operator_config=operator,
        )
        d_periodic = run_periodic_symbolic_arm(
            seed=seed,
            initial_state=initial_state,
            shared_identity_sha256=identity["identity_sha256"],
            shared_predictions=predictions,
            checkpoint_chain=checkpoint_chain,
            rows=symbolic_rows,
            feature_names=preprocessing.feature_columns,
            model_resolver=model_resolver,
            raw_affine=raw_affine,
            operator_config=operator,
        )
        trajectories = (c_arm, d_drift, d_periodic)
        isolation = verify_symbolic_arm_control_plane_isolation(
            trajectories
        )

        arm_files = {
            trajectory.arm: _freeze_arm(
                output_dir / trajectory.arm,
                trajectory,
            )
            for trajectory in trajectories
        }
        manifest = {
            "schema_version": 1,
            "run_id": f"{PRIMARY_RUN_ID}-phase-b-seed-{seed}",
            "seed": seed,
            "git_commit": _git_output("rev-parse", "HEAD"),
            "status": "complete_unscored_symbolic_trajectories",
            "primary_config_manifest_sha256": config[
                "manifest_sha256"
            ],
            "shared_identity_sha256": identity["identity_sha256"],
            "all_phase_a_shared_identity_sha256": {
                str(key): value
                for key, value in sorted(shared_identities.items())
            },
            "operator_config_sha256": operator.sha256(),
            "arm_isolation_sha256": isolation,
            "arms": arm_files,
            "primary_boundary_scored": False,
        }
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        write_json_new(
            output_dir / "phase_b_manifest.json",
            manifest,
        )
    except Exception as exc:
        failure_path = output_dir / "failure.json"
        if not failure_path.exists():
            write_json_new(
                failure_path,
                {
                    "seed": seed,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "primary_boundary_scored": False,
                },
            )
        raise

    verified = verify_phase_b_seed(seed)
    return {
        "status": "phase_b_seed_complete_unscored",
        "seed": seed,
        "phase_b_manifest_sha256": verified[
            "phase_b_manifest_sha256"
        ],
        "arm_isolation_sha256": verified[
            "arm_isolation_sha256"
        ],
        "primary_boundary_scored": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Execute or verify one primary Phase-B symbolic-trajectory seed. "
            "Requires all five frozen Phase-A shared trajectories. "
            "No boundary scoring occurs."
        )
    )
    parser.add_argument("--seed", type=int, required=True, choices=PRIMARY_SEEDS)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (
        verify_phase_b_seed(args.seed)
        if args.verify_only
        else execute_phase_b_seed(args.seed)
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
