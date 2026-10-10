from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_stage9_config import (
    GATE_CONDITIONS,
    OFFLINE_CONDITIONS,
    PRIMARY_SEEDS,
    STAGE9_OUTPUT_ROOT,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_offline import (
    _output_dir as offline_output_dir,
    execute_offline_condition,
    verify_offline_condition,
)
from concept_drift_ids.cd_stage9_phase_a import (
    _seed_dir as phase_a_seed_dir,
    adaptive_condition_ids,
    execute_stage9_phase_a_seed,
    verify_stage9_phase_a_seed,
)
from concept_drift_ids.cd_stage9_phase_b import (
    _phase_b_dir,
    execute_stage9_phase_b_seed,
    verify_stage9_phase_b_seed,
)
from concept_drift_ids.cd_stage9_phase_c import (
    _phase_c_dir,
    execute_stage9_phase_c_seed,
    verify_stage9_phase_c_seed,
)


PLAN_PATH = STAGE9_OUTPUT_ROOT / "execution_plan.json"


def _step(
    *,
    group: str,
    condition: str,
    phase: str,
    seed: int,
) -> dict[str, Any]:
    return {
        "group": group,
        "condition_id": condition,
        "phase": phase,
        "seed": int(seed),
    }


def build_execution_plan(config: Mapping[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    for condition in OFFLINE_CONDITIONS:
        for seed in PRIMARY_SEEDS:
            steps.append(
                _step(
                    group="offline",
                    condition=condition,
                    phase="offline",
                    seed=seed,
                )
            )

    for condition in GATE_CONDITIONS:
        for seed in PRIMARY_SEEDS:
            steps.append(
                _step(
                    group="symbolic_gate",
                    condition=condition,
                    phase="phase_b",
                    seed=seed,
                )
            )
        for seed in PRIMARY_SEEDS:
            steps.append(
                _step(
                    group="symbolic_gate",
                    condition=condition,
                    phase="phase_c",
                    seed=seed,
                )
            )

    for condition in adaptive_condition_ids(config):
        for phase in ("phase_a", "phase_b", "phase_c"):
            for seed in PRIMARY_SEEDS:
                steps.append(
                    _step(
                        group="adaptive",
                        condition=condition,
                        phase=phase,
                        seed=seed,
                    )
                )

    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "frozen_stage9_execution_plan",
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "condition_order": {
            "offline": list(OFFLINE_CONDITIONS),
            "symbolic_gate": list(GATE_CONDITIONS),
            "adaptive": list(adaptive_condition_ids(config)),
        },
        "seed_order": list(PRIMARY_SEEDS),
        "phase_order": {
            "offline": ["offline"],
            "symbolic_gate": ["phase_b", "phase_c"],
            "adaptive": ["phase_a", "phase_b", "phase_c"],
        },
        "steps": steps,
        "outcome_dependent_early_stopping_forbidden": True,
        "technical_failure_policy": (
            "abort_and_preserve_partial_evidence;do_not_delete_or_rerun"
        ),
        "resume_policy": (
            "verify_and_skip_only_complete_steps;"
            "abort_on_existing_partial_or_failed_step"
        ),
    }
    payload["plan_sha256"] = canonical_sha256(payload)
    return payload


def _load_verified_plan(config: Mapping[str, Any]) -> dict[str, Any]:
    payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and stored_payload != canonical_sha256(payload):
        raise ValueError("Stage-9 execution-plan writer hash mismatch.")
    stored_plan = payload.get("plan_sha256")
    core = dict(payload)
    core.pop("plan_sha256", None)
    if stored_plan != canonical_sha256(core):
        raise ValueError("Stage-9 execution-plan canonical hash mismatch.")
    expected = build_execution_plan(config)
    if payload != expected:
        raise ValueError("Stage-9 execution plan differs from frozen config.")
    return payload


def ensure_execution_plan(config: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_execution_plan(config)
    if PLAN_PATH.exists():
        return _load_verified_plan(config)
    STAGE9_OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    write_json_new(PLAN_PATH, expected)
    return _load_verified_plan(config)


def _step_state(step: Mapping[str, Any]) -> tuple[Path, Path, Path]:
    condition = str(step["condition_id"])
    seed = int(step["seed"])
    phase = str(step["phase"])

    if phase == "offline":
        root = offline_output_dir(condition, seed)
        return root, root / "result.json", root / "failure.json"
    if phase == "phase_a":
        root = phase_a_seed_dir(condition, seed)
        return root, root / "run_manifest.json", root / "failure.json"
    if phase == "phase_b":
        root = _phase_b_dir(condition, seed)
        return root, root / "phase_b_manifest.json", root / "failure.json"
    if phase == "phase_c":
        root = _phase_c_dir(condition, seed)
        return root, root / "phase_c_seed_manifest.json", root / "failure.json"
    raise ValueError(f"Unknown Stage-9 execution phase: {phase}")


def _actions(
    step: Mapping[str, Any],
) -> tuple[Callable[..., dict[str, Any]], Callable[..., dict[str, Any]]]:
    phase = str(step["phase"])
    if phase == "offline":
        return execute_offline_condition, verify_offline_condition
    if phase == "phase_a":
        return execute_stage9_phase_a_seed, verify_stage9_phase_a_seed
    if phase == "phase_b":
        return execute_stage9_phase_b_seed, verify_stage9_phase_b_seed
    if phase == "phase_c":
        return execute_stage9_phase_c_seed, verify_stage9_phase_c_seed
    raise ValueError(f"Unknown Stage-9 execution phase: {phase}")


def _run_or_verify_step(
    step: Mapping[str, Any],
    *,
    verify_only: bool,
) -> dict[str, Any]:
    root, completion, failure = _step_state(step)
    execute, verify = _actions(step)
    condition = str(step["condition_id"])
    seed = int(step["seed"])

    if failure.exists():
        raise RuntimeError(
            "Stage-9 execution encountered preserved failed evidence: "
            f"{failure}"
        )

    if completion.exists():
        result = verify(condition, seed)
        return {
            "step": dict(step),
            "action": "verified_existing_complete",
            "result": result,
        }

    if root.exists():
        raise RuntimeError(
            "Stage-9 execution found an incomplete write-once step and will not "
            f"resume or overwrite it: {root}"
        )

    if verify_only:
        raise FileNotFoundError(
            f"Stage-9 required step is incomplete: {condition}/{step['phase']}/seed-{seed}"
        )

    result = execute(condition, seed)
    verified = verify(condition, seed)
    return {
        "step": dict(step),
        "action": "executed_and_verified",
        "result": result,
        "verification": verified,
    }


def execute_all_stage9(*, verify_only: bool = False) -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    if verify_only:
        if not PLAN_PATH.is_file():
            raise FileNotFoundError(
                "Stage-9 execution plan is absent; verify-only must not create it."
            )
        plan = _load_verified_plan(config)
    else:
        plan = ensure_execution_plan(config)
    completed = 0
    existing = 0

    for step in plan["steps"]:
        record = _run_or_verify_step(step, verify_only=verify_only)
        completed += 1
        if record["action"] == "verified_existing_complete":
            existing += 1

    return {
        "status": (
            "stage9_full_matrix_verified"
            if verify_only
            else "stage9_full_matrix_executed_and_verified"
        ),
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "step_count": len(plan["steps"]),
        "completed_step_count": completed,
        "preexisting_complete_step_count": existing,
        "all_frozen_conditions_completed": completed == len(plan["steps"]),
        "outcome_dependent_early_stopping_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            execute_all_stage9(verify_only=args.verify_only),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
