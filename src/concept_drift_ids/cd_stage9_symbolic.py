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
from concept_drift_ids.cd_evidence import read_jsonl, write_jsonl_new
from concept_drift_ids.cd_primary_adapter import (
    load_accepted_system_a_model,
    load_primary_stream,
)
from concept_drift_ids.cd_primary_phase_a import verify_phase_a_seed
from concept_drift_ids.cd_r0_lifecycle import migrate_accepted_r0_v2_state
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_stage9_config import (
    PRIMARY_SEEDS,
    PROJECT_ROOT,
    STATIC_OPERATOR,
    STAGE9_OUTPUT_ROOT,
    STAGE9_RUN_ID,
    _git_output,
    _verify_parent_primary_config,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_phase_a import (
    ADAPTIVE_CONDITIONS,
    verify_stage9_phase_a_seed,
)
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
SYMBOLIC_CONDITIONS = ("G_STATIC_GATE", *ADAPTIVE_CONDITIONS)
PRIMARY_HEAVY_ROOT = PROJECT_ROOT / "artifacts" / "cd_primary_v1"


def _phase_a_dir(condition_id: str, seed: int) -> Path:
    if condition_id == "G_STATIC_GATE":
        return PRIMARY_HEAVY_ROOT / "phase_a_shared_control_plane" / f"seed-{seed}"
    return (
        STAGE9_OUTPUT_ROOT
        / "adaptive"
        / condition_id
        / "phase_a_shared_control_plane"
        / f"seed-{seed}"
    )


def _phase_b_dir(condition_id: str, seed: int) -> Path:
    if condition_id == "G_STATIC_GATE":
        return (
            STAGE9_OUTPUT_ROOT
            / "symbolic_gate"
            / condition_id
            / "phase_b_symbolic_arms"
            / f"seed-{seed}"
        )
    return (
        STAGE9_OUTPUT_ROOT
        / "adaptive"
        / condition_id
        / "phase_b_symbolic_arms"
        / f"seed-{seed}"
    )


def _operator(condition_id: str) -> SymbolicOperatorConfig:
    return STATIC_OPERATOR if condition_id == "G_STATIC_GATE" else SymbolicOperatorConfig()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verified_json(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError(f"JSON writer payload hash mismatch: {path}")
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
    expected_run_id: str,
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
        raise ValueError("Initial System-A checkpoint absent from shared chain.")

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
            raise ValueError("Requested model absent from shared checkpoint chain.")
        path = child_paths.get(checkpoint_sha256)
        if path is None:
            raise FileNotFoundError("Shared chain references missing child checkpoint.")
        if sha256_file(path) != checkpoint_sha256:
            raise ValueError("Child checkpoint raw file hash mismatch.")
        payload = torch.load(path, map_location="cpu", weights_only=False)
        model = _new_model()
        model.load_state_dict(payload["state_dict"])
        model.cpu().eval()
        expected_state = str(chain_by_file[checkpoint_sha256]["child_state_sha256"])
        if str(payload["state_sha256"]) != expected_state:
            raise ValueError("Child checkpoint embedded state identity mismatch.")
        if state_dict_sha256(model) != expected_state:
            raise ValueError("Child checkpoint reconstructed state mismatch.")
        metadata = payload["metadata"]
        if str(metadata["run_id"]) != expected_run_id:
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
        raise ValueError("Stage-9 stream and shared predictions differ in size.")
    out: list[SharedSymbolicRow] = []
    for index, (stream, prediction) in enumerate(zip(stream_rows, predictions)):
        if stream.row_id != prediction["row_id"]:
            raise ValueError("Stage-9 symbolic row identity differs from Phase A.")
        if int(prediction["origin_index"]) != index:
            raise ValueError("Stage-9 shared prediction order changed.")
        out.append(
            SharedSymbolicRow(
                row_id=stream.row_id,
                origin_index=index,
                maturity_index=int(prediction["maturity_index"]),
                features=np.asarray(stream.features, dtype=np.float32),
                true_label=int(stream.label),
                neural_probability=float(prediction["neural_probability"]),
                neural_checkpoint_sha256=str(prediction["checkpoint_sha256"]),
            )
        )
    return tuple(out)


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
        "parent_rule_base_version_id": record.parent_rule_base_version_id,
        "result_rule_base_version_id": record.result_rule_base_version_id,
        "parent_rule_base_sha256": record.parent_rule_base_sha256,
        "result_rule_base_sha256": record.result_rule_base_sha256,
        "history_sha256": record.history_sha256,
        "candidate_count": int(record.candidate_count),
        "shap_seconds": float(record.shap_seconds),
        "surrogate_seconds": float(record.surrogate_seconds),
        "lifecycle_seconds": float(record.lifecycle_seconds),
        "validation_wait_rows": record.validation_wait_rows,
        "lifecycle": (
            {
                "status": lifecycle.maintenance_status,
                "published": lifecycle.published,
                "decisions": list(lifecycle.decisions),
                "staleness_snapshot": list(lifecycle.staleness_snapshot),
                "candidate_evidence": list(lifecycle.candidate_evidence),
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
        raise FileExistsError(f"Refusing to overwrite Stage-9 symbolic arm: {arm_dir}")
    arm_dir.mkdir(parents=True, exist_ok=False)

    initial_path = arm_dir / "initial_state.json"
    initial_sha = write_json_new(initial_path, trajectory.initial_state.to_dict())
    final_path = arm_dir / "final_state.json"
    final_sha = write_json_new(final_path, trajectory.final_state.to_dict())
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
        path = versions_dir / f"{ordinal:04d}-{state.rule_base_version_id}.json"
        digest = write_json_new(
            path,
            {"effective_index": int(effective_index), "state": state.to_dict()},
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
        "initial_state": {"path": initial_path.name, "sha256": initial_sha},
        "final_state": {"path": final_path.name, "sha256": final_sha},
        "maintenance": {"path": maintenance_path.name, "sha256": maintenance_sha},
        **version_files,
    }
    manifest = {
        "schema_version": 1,
        "seed": trajectory.seed,
        "arm": trajectory.arm,
        "operator_config_sha256": trajectory.operator_config_sha256,
        "shared_identity_sha256": trajectory.shared_identity_sha256,
        "initial_rule_base_version_id": trajectory.initial_state.rule_base_version_id,
        "initial_rule_base_sha256": trajectory.initial_state.canonical_sha256,
        "final_rule_base_version_id": trajectory.final_state.rule_base_version_id,
        "final_rule_base_sha256": trajectory.final_state.canonical_sha256,
        "final_history_sha256": trajectory.final_state.history_sha256,
        "publications": publications,
        "maintenance_summary": summarize_symbolic_maintenance(trajectory.maintenance),
        "files": files,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    manifest_path = arm_dir / "arm_manifest.json"
    manifest_file_sha = write_json_new(manifest_path, manifest)
    return {
        "path": manifest_path.relative_to(arm_dir.parent).as_posix(),
        "sha256": manifest_file_sha,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def _load_arm(condition_id: str, seed: int, arm: str) -> SymbolicArmTrajectory:
    if arm not in ARM_NAMES:
        raise ValueError(f"Unknown Stage-9 symbolic arm: {arm}")
    arm_dir = _phase_b_dir(condition_id, seed) / arm
    manifest = _verified_json(arm_dir / "arm_manifest.json")
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError("Stage-9 arm manifest canonical hash mismatch.")

    for descriptor in manifest["files"].values():
        path = arm_dir / str(descriptor["path"])
        if not path.is_file() or sha256_file(path) != str(descriptor["sha256"]):
            raise ValueError(f"Stage-9 symbolic arm file identity mismatch: {path}")

    initial = rule_base_state_from_dict(
        _verified_json(arm_dir / manifest["files"]["initial_state"]["path"])
    )
    final = rule_base_state_from_dict(
        _verified_json(arm_dir / manifest["files"]["final_state"]["path"])
    )
    verify_lifecycle_state(initial)
    verify_lifecycle_state(final)

    publications: list[tuple[int, RuleBaseState]] = []
    previous = initial
    previous_effective = -1
    for item in manifest["publications"]:
        descriptor = manifest["files"][item["file_key"]]
        payload = _verified_json(arm_dir / descriptor["path"])
        state = rule_base_state_from_dict(payload["state"])
        verify_lifecycle_state(state)
        effective = int(payload["effective_index"])
        if effective <= previous_effective:
            raise ValueError("Stage-9 symbolic publication clocks are not increasing.")
        if state.parent_version_id != previous.rule_base_version_id:
            raise ValueError("Stage-9 symbolic publication parent version mismatch.")
        if state.parent_version_sha256 != previous.canonical_sha256:
            raise ValueError("Stage-9 symbolic publication parent hash mismatch.")
        if state.version_number != previous.version_number + 1:
            raise ValueError("Stage-9 symbolic publication version sequence mismatch.")
        if state.canonical_sha256 != item["canonical_sha256"]:
            raise ValueError("Stage-9 symbolic publication state identity mismatch.")
        if state.history_sha256 != item["history_sha256"]:
            raise ValueError("Stage-9 symbolic publication history mismatch.")
        publications.append((effective, state))
        previous = state
        previous_effective = effective

    if publications:
        if final.canonical_sha256 != publications[-1][1].canonical_sha256:
            raise ValueError("Stage-9 final state differs from last publication.")
    elif final.canonical_sha256 != initial.canonical_sha256:
        raise ValueError("Stage-9 final state changed without publication.")

    return SymbolicArmTrajectory(
        seed=seed,
        arm=arm,
        operator_config_sha256=str(manifest["operator_config_sha256"]),
        shared_identity_sha256=str(manifest["shared_identity_sha256"]),
        initial_state=initial,
        final_state=final,
        maintenance=(),
        publications=tuple(publications),
    )


def _verify_generation_validation_disjointness(condition_id: str, seed: int) -> None:
    for arm in ("d_drift", "d_periodic"):
        path = _phase_b_dir(condition_id, seed) / arm / "maintenance.jsonl"
        records = read_jsonl(path)
        for record in records:
            generation = set(record.get("generation_row_ids") or [])
            validation = set(record.get("validation_row_ids") or [])
            if generation.intersection(validation):
                raise ValueError(
                    f"Stage-9 generation/validation overlap: {condition_id} seed={seed} arm={arm}"
                )


def _shared_phase_a_identity(
    condition_id: str,
    seed: int,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    if condition_id == "G_STATIC_GATE":
        primary = _verify_parent_primary_config()
        return verify_phase_a_seed(seed, config=primary)
    return verify_stage9_phase_a_seed(condition_id, seed, config=config)


def _expected_phase_a_run_id(condition_id: str, seed: int) -> str:
    if condition_id == "G_STATIC_GATE":
        return f"cd-primary-v1-phase-a-seed-{seed}"
    return f"{STAGE9_RUN_ID}-{condition_id}-phase-a-seed-{seed}"


def execute_stage9_symbolic_seed(condition_id: str, seed: int) -> dict[str, Any]:
    if condition_id not in SYMBOLIC_CONDITIONS:
        raise ValueError(f"Unsupported Stage-9 symbolic condition: {condition_id}")
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")

    config = verify_stage9_config_for_execution()
    configure_torch_primary_runtime()

    if condition_id == "A_BASELINE" and not bool(config["conditions"][condition_id]["required"]):
        raise RuntimeError("A_BASELINE is not required on the frozen Stage-9 runtime.")

    # Freeze and verify all five shared trajectories before any symbolic treatment.
    phase_a_verified = {
        other: _shared_phase_a_identity(
            condition_id,
            other,
            config=config,
        )
        for other in PRIMARY_SEEDS
    }
    all_shared = {
        str(other): phase_a_verified[other]["shared_identity_sha256"]
        for other in PRIMARY_SEEDS
    }

    output_dir = _phase_b_dir(condition_id, seed)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 Phase-B output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    phase_a_dir = _phase_a_dir(condition_id, seed)
    identity = _verified_json(phase_a_dir / "shared_identity.json")["shared_identity"]
    if identity["identity_sha256"] != phase_a_verified[seed]["shared_identity_sha256"]:
        raise ValueError("Stage-9 Phase-A shared identity changed before symbolic treatment.")

    operator = _operator(condition_id)
    run_id = f"{STAGE9_RUN_ID}-{condition_id}-phase-b-seed-{seed}"
    write_json_new(
        output_dir / "attempt.json",
        {
            "run_id": run_id,
            "condition_id": condition_id,
            "seed": seed,
            "git_commit": _git_output("rev-parse", "HEAD"),
            "stage9_config_manifest_sha256": config["manifest_sha256"],
            "shared_identity_sha256": identity["identity_sha256"],
            "all_phase_a_shared_identity_sha256": all_shared,
            "operator_config_sha256": operator.sha256(),
            "boundary_metadata_supplied_to_symbolic_operator": False,
        },
    )

    try:
        predictions = read_jsonl(phase_a_dir / "predictions.jsonl")
        events = read_jsonl(phase_a_dir / "events.jsonl")
        replay = read_jsonl(phase_a_dir / "replay_transactions.jsonl")
        checkpoint_chain = read_jsonl(phase_a_dir / "checkpoint_chain.jsonl")

        preprocessing = load_frozen_preprocessing()
        stream_rows = load_primary_stream(preprocessing=preprocessing)
        symbolic_rows = _shared_symbolic_rows(
            stream_rows=stream_rows,
            predictions=predictions,
        )
        initial_checkpoint_sha256 = str(checkpoint_chain[0]["checkpoint_file_sha256"])
        initial_state = migrate_accepted_r0_v2_state(
            seed,
            neural_checkpoint_sha256=initial_checkpoint_sha256,
        )
        model_resolver = _build_model_resolver(
            seed,
            phase_a_dir=phase_a_dir,
            checkpoint_chain=checkpoint_chain,
            expected_run_id=_expected_phase_a_run_id(condition_id, seed),
        )
        raw_affine = {
            feature: (
                float(preprocessing.means[index]),
                float(preprocessing.scales[index]),
            )
            for index, feature in enumerate(preprocessing.feature_columns)
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
        isolation = verify_symbolic_arm_control_plane_isolation(trajectories)
        arm_files = {
            trajectory.arm: _freeze_arm(
                output_dir / trajectory.arm,
                trajectory,
            )
            for trajectory in trajectories
        }
        manifest = {
            "schema_version": 1,
            "run_id": run_id,
            "condition_id": condition_id,
            "seed": seed,
            "git_commit": _git_output("rev-parse", "HEAD"),
            "status": "complete_unscored_stage9_symbolic_trajectories",
            "stage9_config_manifest_sha256": config["manifest_sha256"],
            "shared_identity_sha256": identity["identity_sha256"],
            "all_phase_a_shared_identity_sha256": all_shared,
            "operator_config_sha256": operator.sha256(),
            "arm_isolation_sha256": isolation,
            "arms": arm_files,
            "boundary_metadata_supplied_to_symbolic_operator": False,
        }
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        write_json_new(output_dir / "phase_b_manifest.json", manifest)
        verified = verify_stage9_symbolic_seed(condition_id, seed)
    except Exception as exc:
        failure = output_dir / "failure.json"
        if not failure.exists():
            write_json_new(
                failure,
                {
                    "condition_id": condition_id,
                    "seed": seed,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "boundary_metadata_supplied_to_symbolic_operator": False,
                },
            )
        raise

    return {
        "status": "stage9_symbolic_seed_complete_unscored",
        "condition_id": condition_id,
        "seed": seed,
        "phase_b_manifest_sha256": verified["phase_b_manifest_sha256"],
        "arm_isolation_sha256": verified["arm_isolation_sha256"],
    }


def verify_stage9_symbolic_seed(
    condition_id: str,
    seed: int,
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if condition_id not in SYMBOLIC_CONDITIONS:
        raise ValueError(f"Unsupported Stage-9 symbolic condition: {condition_id}")
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")
    if config is None:
        config = verify_stage9_config_for_execution(require_clean=False)

    phase_a_verified = {
        other: _shared_phase_a_identity(condition_id, other, config=config)
        for other in PRIMARY_SEEDS
    }
    expected_shared = phase_a_verified[seed]["shared_identity_sha256"]
    expected_all = {
        str(other): phase_a_verified[other]["shared_identity_sha256"]
        for other in PRIMARY_SEEDS
    }

    output_dir = _phase_b_dir(condition_id, seed)
    manifest = _verified_json(output_dir / "phase_b_manifest.json")
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError("Stage-9 Phase-B manifest canonical hash mismatch.")
    if manifest["status"] != "complete_unscored_stage9_symbolic_trajectories":
        raise ValueError("Stage-9 Phase-B status changed.")
    if int(manifest["seed"]) != seed or manifest["condition_id"] != condition_id:
        raise ValueError("Stage-9 Phase-B condition/seed identity mismatch.")
    if manifest["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 Phase-B references wrong config.")
    if manifest["shared_identity_sha256"] != expected_shared:
        raise ValueError("Stage-9 Phase-B shared identity differs from verified Phase A.")
    if manifest["all_phase_a_shared_identity_sha256"] != expected_all:
        raise ValueError("Stage-9 all-seed Phase-A identity map changed.")
    if manifest.get("boundary_metadata_supplied_to_symbolic_operator") is not False:
        raise ValueError("Boundary metadata contamination flag is not false.")

    expected_operator = _operator(condition_id).sha256()
    if manifest["operator_config_sha256"] != expected_operator:
        raise ValueError("Stage-9 symbolic operator identity changed.")

    for arm in ARM_NAMES:
        descriptor = manifest["arms"].get(arm)
        if descriptor is None:
            raise ValueError(f"Missing Stage-9 arm descriptor: {arm}")
        path = output_dir / str(descriptor["path"])
        if sha256_file(path) != str(descriptor["sha256"]):
            raise ValueError("Stage-9 arm-manifest file hash mismatch.")
        arm_manifest = _verified_json(path)
        if arm_manifest.get("manifest_sha256") != descriptor["manifest_sha256"]:
            raise ValueError("Stage-9 arm canonical identity mismatch.")
        if arm_manifest["shared_identity_sha256"] != expected_shared:
            raise ValueError("Stage-9 arm detached from shared Phase A.")
        if arm_manifest["operator_config_sha256"] != expected_operator:
            raise ValueError("Stage-9 arm operator identity changed.")

    trajectories = tuple(_load_arm(condition_id, seed, arm) for arm in ARM_NAMES)
    isolation = verify_symbolic_arm_control_plane_isolation(trajectories)
    if isolation != manifest["arm_isolation_sha256"]:
        raise ValueError("Stage-9 symbolic arm-isolation identity mismatch.")
    _verify_generation_validation_disjointness(condition_id, seed)

    return {
        "status": "stage9_symbolic_seed_verified_unscored",
        "condition_id": condition_id,
        "seed": seed,
        "phase_b_manifest_sha256": stored,
        "arm_isolation_sha256": isolation,
        "shared_identity_sha256": expected_shared,
        "operator_config_sha256": expected_operator,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute or verify Stage-9 symbolic treatment.")
    parser.add_argument("--condition", required=True, choices=SYMBOLIC_CONDITIONS)
    parser.add_argument("--seed", required=True, type=int, choices=PRIMARY_SEEDS)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.verify_only:
        result = verify_stage9_symbolic_seed(args.condition, args.seed)
    else:
        result = execute_stage9_symbolic_seed(args.condition, args.seed)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
