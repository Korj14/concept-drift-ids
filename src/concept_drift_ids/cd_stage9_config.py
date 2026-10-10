from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

from concept_drift_ids.cd_control_plane import ADWIN_CONFIG, canonical_sha256, write_json_new
from concept_drift_ids.cd_implementation_preflight import PROJECT_ROOT
from concept_drift_ids.cd_primary_config import (
    EXPECTED_REQUIREMENTS_NORMALIZED_SHA256,
    PRIMARY_SEEDS,
)
from concept_drift_ids.cd_runtime import (
    PRIMARY_THREAD_ENV,
    configure_torch_primary_runtime,
    verify_locked_distributions,
)
from concept_drift_ids.cd_shared_runner import ControlPlaneConfig
from concept_drift_ids.cd_symbolic_arms import SymbolicOperatorConfig
from concept_drift_ids.scenario_manifest import sha256_normalized_text


STAGE9_SCHEMA_VERSION = 1
STAGE9_RUN_ID = "cd-robustness-v1"
STAGE9_PROTOCOL_PATH = "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md"
STAGE8_PARENT_EVIDENCE_COMMIT = "c2ded83b8195b9321e715626c1f305f9627936e8"
STAGE8_CLOSURE_COMMIT = "f8a424389056a048a6ad6be0b744bf6d12b69df2"
STAGE8_COMPACT_EXPORT_MANIFEST_SHA256 = (
    "409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523"
)
STAGE8_CONFIRMATORY_AGGREGATE_SHA256 = (
    "1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d"
)
STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256 = (
    "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222"
)
STAGE8_UPSTREAM_ARTIFACT_CONFIG_MANIFEST_SHA256 = (
    "3e3f768b5aa32f469440bb334508f747bbf2f7f5b08d9570a7aef2dbb9cb0257"
)
STAGE8_CORRECTED_CONFIG_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "cd_primary_run_config_v1_1.json"
)
STAGE8_COMPACT_ROOT = PROJECT_ROOT / "results" / "frozen" / "cd_primary_v1"
STAGE9_CONFIG_PATH = PROJECT_ROOT / "data" / "manifests" / "cd_stage9_run_config_v1.json"
STAGE9_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "cd_robustness_v1"
STAGE9_COMPACT_ROOT = PROJECT_ROOT / "results" / "frozen" / "cd_robustness_v1"

OFFLINE_CONDITIONS = (
    "lambda_0_7",
    "lambda_0_9",
    "lambda_1_0",
    "window_2500",
    "window_10000",
)
GATE_CONDITIONS = ("static_symbolic_gate",)
ADAPTIVE_VARIANTS = (
    "latency_0",
    "latency_10000",
    "page_hinkley_hard_error",
    "adwin_brier",
    "no_replay",
)
MATCHED_BASELINE_CONDITION = "matched_primary_baseline"

# Prospectively frozen before any Stage-9 robustness outcome access.
PAGE_HINKLEY_CONFIG = {
    "min_instances": 30,
    "delta": 0.005,
    "threshold": 50.0,
    "alpha": 0.9999,
    "mode": "both",
}

STATIC_GATE_CONFIG = {
    "min_support": 0.001,
    "min_covered": 100,
    "min_class_precision": 0.80,
    "min_neural_fidelity": 0.90,
    "bootstrap_replicates": 100,
    "min_stability": 0.90,
    "max_complexity": 4,
    "use_wilson_lcb": False,
}

REUSED_STAGE8_SOURCE_PATHS = (
    "src/concept_drift_ids/neural.py",
    "src/concept_drift_ids/frozen_preprocessing.py",
    "src/concept_drift_ids/scenario_loader.py",
    "src/concept_drift_ids/system_a.py",
    "src/concept_drift_ids/cd_control_plane.py",
    "src/concept_drift_ids/cd_evidence.py",
    "src/concept_drift_ids/cd_runtime.py",
    "src/concept_drift_ids/cd_shared_runner.py",
    "src/concept_drift_ids/cd_symbolic_lifecycle.py",
    "src/concept_drift_ids/cd_symbolic_candidates.py",
    "src/concept_drift_ids/cd_symbolic_arms.py",
    "src/concept_drift_ids/cd_symbolic_runner.py",
    "src/concept_drift_ids/cd_symbolic_evidence.py",
    "src/concept_drift_ids/cd_symbolic_evaluation.py",
    "src/concept_drift_ids/cd_analysis.py",
    "src/concept_drift_ids/cd_r0_lifecycle.py",
    "src/concept_drift_ids/cd_implementation_preflight.py",
    "src/concept_drift_ids/cd_primary_config.py",
    "src/concept_drift_ids/cd_primary_adapter.py",
    "src/concept_drift_ids/cd_primary_phase_a.py",
    "src/concept_drift_ids/cd_primary_phase_b.py",
    "src/concept_drift_ids/cd_primary_phase_c.py",
)

STAGE9_SOURCE_PATHS = (
    "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md",
    "STAGE9_IMPLEMENTATION.md",
    "src/concept_drift_ids/cd_stage9_config.py",
    "src/concept_drift_ids/cd_stage9_monitor.py",
    "src/concept_drift_ids/cd_stage9_shared_runner.py",
    "src/concept_drift_ids/cd_stage9_offline.py",
    "src/concept_drift_ids/cd_stage9_phase_a.py",
    "src/concept_drift_ids/cd_stage9_phase_b.py",
    "src/concept_drift_ids/cd_stage9_phase_c.py",
    "src/concept_drift_ids/cd_stage9_export.py",
    "src/concept_drift_ids/cd_stage9_execute.py",
    "tests/test_cd_stage9_unit.py",
    "run_stage9.py",
    "scripts/run_stage9.ps1",
    ".github/workflows/stage9-unit.yml",
    "data/manifests/.gitattributes",
    "results/frozen/.gitattributes",
    "src/concept_drift_ids/scenario_manifest.py",
    "src/concept_drift_ids/symbolic.py",
    *REUSED_STAGE8_SOURCE_PATHS,
)


def _git(
    *args: str,
    project_root: Path = PROJECT_ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _git_output(*args: str, project_root: Path = PROJECT_ROOT) -> str:
    return _git(*args, project_root=project_root).stdout.strip()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_manifest(path: Path) -> tuple[dict[str, Any], str]:
    payload = _read_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and stored_payload != canonical_sha256(payload):
        raise ValueError(f"Payload hash mismatch: {path}")
    stored = payload.pop("manifest_sha256", None)
    if stored != canonical_sha256(payload):
        raise ValueError(f"Canonical manifest hash mismatch: {path}")
    return payload, str(stored)


def _text_hashes(paths: Sequence[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for relative in paths:
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Missing Stage-9 source: {path}")
        out[relative] = sha256_normalized_text(path)
    return out


def _require_clean_for_preparation() -> None:
    status = _git_output("status", "--porcelain")
    if status:
        raise RuntimeError("Stage-9 preparation requires a clean worktree.")


def _require_stage8_closure_ancestor() -> None:
    result = _git(
        "merge-base",
        "--is-ancestor",
        STAGE8_CLOSURE_COMMIT,
        "HEAD",
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            "Stage-9 source HEAD does not descend from the accepted Stage-8 closure."
        )


def _require_no_stage9_outputs_before_preparation() -> None:
    occupied = [
        path
        for path in (STAGE9_OUTPUT_ROOT, STAGE9_COMPACT_ROOT)
        if path.exists()
    ]
    if occupied:
        raise RuntimeError(
            "Stage-9 preparation requires no pre-existing robustness output roots: "
            + ", ".join(str(path) for path in occupied)
        )


def _requirements_identity() -> dict[str, Any]:
    path = PROJECT_ROOT / "requirements-lock.txt"
    normalized = sha256_normalized_text(path)
    if normalized != EXPECTED_REQUIREMENTS_NORMALIZED_SHA256:
        raise ValueError("Frozen requirements lock identity changed.")
    installed = verify_locked_distributions(lock_path=path)
    return {
        "path": "requirements-lock.txt",
        "binding_normalized_text_sha256": normalized,
        "installed_distributions": installed,
        "installed_distributions_sha256": canonical_sha256(installed),
    }


def _runtime_inventory() -> dict[str, Any]:
    configured = configure_torch_primary_runtime()
    thread_env = {key: __import__("os").environ.get(key) for key in PRIMARY_THREAD_ENV}
    missing = [key for key, value in thread_env.items() if value != PRIMARY_THREAD_ENV[key]]
    if missing:
        raise RuntimeError(f"Stage-9 thread environment mismatch: {missing}")
    if sys.version_info[:3] != (3, 11, 9):
        raise RuntimeError("Stage-9 requires Python 3.11.9 exactly.")
    if torch.cuda.is_available():
        raise RuntimeError("Stage-9 scientific runtime must be CPU-only.")
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "torch_version": torch.__version__,
        "torch_cuda_available": bool(torch.cuda.is_available()),
        "thread_environment": thread_env,
        "torch_deterministic_algorithms": bool(
            torch.are_deterministic_algorithms_enabled()
        ),
        "torch_num_threads": int(torch.get_num_threads()),
        "torch_num_interop_threads": int(torch.get_num_interop_threads()),
        "configured_runtime": {
            "torch_deterministic_algorithms": configured[
                "torch_deterministic_algorithms"
            ],
            "torch_num_threads": configured["torch_num_threads"],
            "torch_num_interop_threads": configured["torch_num_interop_threads"],
        },
    }


def _runtime_fingerprint(
    runtime: Mapping[str, Any],
    *,
    locked_distributions_sha256: str,
) -> dict[str, Any]:
    return {
        "platform": str(runtime["platform"]),
        "processor": str(runtime["processor"]),
        "python_version": str(runtime["python_version"]),
        "python_implementation": str(runtime["python_implementation"]),
        "torch_version": str(runtime["torch_version"]),
        "torch_deterministic_algorithms": bool(
            runtime["torch_deterministic_algorithms"]
        ),
        "torch_num_threads": int(runtime["torch_num_threads"]),
        "torch_num_interop_threads": int(runtime["torch_num_interop_threads"]),
        "thread_environment": dict(runtime["thread_environment"]),
        "locked_distributions_sha256": str(locked_distributions_sha256),
    }


def _primary_runtime_reference() -> dict[str, Any]:
    seed_fingerprints: dict[str, dict[str, Any]] = {}
    for seed in PRIMARY_SEEDS:
        path = (
            STAGE8_COMPACT_ROOT
            / "phase_a_shared_control_plane"
            / f"seed-{seed}"
            / "run_manifest.json"
        )
        payload, _ = _canonical_manifest(path)
        runtime = dict(payload["runtime"])
        seed_fingerprints[str(seed)] = _runtime_fingerprint(
            runtime,
            locked_distributions_sha256=str(
                runtime["locked_distributions_sha256"]
            ),
        )

    unique = {
        canonical_sha256(fingerprint)
        for fingerprint in seed_fingerprints.values()
    }
    if len(unique) != 1:
        raise ValueError(
            "Frozen Stage-8 Phase-A seeds do not share one runtime fingerprint."
        )
    common = seed_fingerprints[str(PRIMARY_SEEDS[0])]
    return {
        "seed_fingerprints": seed_fingerprints,
        "common_fingerprint": common,
        "common_fingerprint_sha256": canonical_sha256(common),
    }


def _runtime_requires_matched_baseline(
    current: Mapping[str, Any],
    primary: Mapping[str, Any],
    requirements: Mapping[str, Any],
) -> bool:
    current_fingerprint = _runtime_fingerprint(
        current,
        locked_distributions_sha256=str(
            requirements["installed_distributions_sha256"]
        ),
    )
    return current_fingerprint != primary["common_fingerprint"]


def _verify_reused_stage8_source_tree(
    corrected_config: Mapping[str, Any],
) -> dict[str, str]:
    expected = dict(corrected_config["scientific_source_hashes"])
    current: dict[str, str] = {}
    for relative in REUSED_STAGE8_SOURCE_PATHS:
        if relative not in expected:
            raise ValueError(
                f"Reused Stage-8 source lacks frozen identity: {relative}"
            )
        expected_hash = expected[relative]
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing Stage-8 scientific source reused by Stage 9: {path}"
            )
        observed = sha256_normalized_text(path)
        if observed != str(expected_hash):
            raise ValueError(
                "Stage-8 scientific source changed before Stage-9 reuse: "
                f"{relative}"
            )
        current[relative] = observed
    return current


def _verify_stage8_parent() -> dict[str, Any]:
    corrected, corrected_hash = _canonical_manifest(STAGE8_CORRECTED_CONFIG_PATH)
    if corrected_hash != STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256:
        raise ValueError("Unexpected Stage-8 corrected config identity.")
    if (
        corrected.get("upstream_artifact_config_manifest_sha256")
        != STAGE8_UPSTREAM_ARTIFACT_CONFIG_MANIFEST_SHA256
    ):
        raise ValueError("Unexpected Stage-8 upstream artifact-config identity.")
    reused_source_hashes = _verify_reused_stage8_source_tree(corrected)

    compact, compact_hash = _canonical_manifest(
        STAGE8_COMPACT_ROOT / "compact_export_manifest.json"
    )
    if compact_hash != STAGE8_COMPACT_EXPORT_MANIFEST_SHA256:
        raise ValueError("Stage-8 compact evidence identity changed.")
    if (
        compact["primary_config_manifest_sha256"]
        != STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256
    ):
        raise ValueError("Stage-8 compact evidence corrected-config binding changed.")
    if (
        compact["parent_primary_config_manifest_sha256"]
        != STAGE8_UPSTREAM_ARTIFACT_CONFIG_MANIFEST_SHA256
    ):
        raise ValueError("Stage-8 compact evidence upstream-config binding changed.")
    ancestor = _git(
        "merge-base",
        "--is-ancestor",
        STAGE8_PARENT_EVIDENCE_COMMIT,
        "HEAD",
        check=False,
    )
    if ancestor.returncode != 0:
        raise ValueError("Current Stage-9 source does not descend from Stage-8 evidence.")

    confirmatory, confirmatory_hash = _canonical_manifest(
        STAGE8_COMPACT_ROOT
        / "phase_c_offline_evaluation_v1_1"
        / "confirmatory_analysis.json"
    )
    if confirmatory_hash != STAGE8_CONFIRMATORY_AGGREGATE_SHA256:
        raise ValueError("Stage-8 confirmatory aggregate identity changed.")
    if (
        confirmatory["primary_config_manifest_sha256"]
        != STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256
    ):
        raise ValueError("Stage-8 confirmatory corrected-config binding changed.")

    return {
        "corrected_config_manifest_sha256": corrected_hash,
        "compact_export_manifest_sha256": compact_hash,
        "confirmatory_aggregate_sha256": confirmatory_hash,
        "reused_stage8_scientific_source_tree_sha256": canonical_sha256(
            reused_source_hashes
        ),
    }


def _stage8_frozen_primary_contract() -> dict[str, Any]:
    corrected, corrected_hash = _canonical_manifest(
        STAGE8_CORRECTED_CONFIG_PATH
    )
    if corrected_hash != STAGE8_CORRECTED_CONFIG_MANIFEST_SHA256:
        raise ValueError("Unexpected Stage-8 corrected config identity.")
    keys = (
        "scenario",
        "system_a",
        "r0_v2",
        "primary_control_plane",
        "primary_symbolic_operator",
        "fusion",
        "analysis",
    )
    contract = {key: corrected[key] for key in keys}
    return {
        "source_config_manifest_sha256": corrected_hash,
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
    }


def _condition_spec(
    config: Mapping[str, Any],
    condition: str,
) -> Mapping[str, Any]:
    for family in ("offline", "symbolic_gate", "adaptive"):
        specs = config["conditions"][family]
        if condition in specs:
            return specs[condition]
    raise ValueError(f"Unknown frozen Stage-9 condition: {condition}")


def global_artifact_identity_context(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    contract = config["frozen_primary_contract"]["contract"]
    scenario = contract["scenario"]
    return {
        "stage8_parent_evidence_commit": config["stage8_parent"]["evidence_commit"],
        "stage8_closure_commit": config["stage8_parent"]["closure_commit"],
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "runtime_identity_sha256": canonical_sha256(config["runtime"]),
        "scenario_manifest_canonical_sha256": scenario[
            "manifest_canonical_sha256"
        ],
        "preprocessing_state_hash": scenario["preprocessing_state_hash"],
        "system_a_manifest_sha256": contract["system_a"]["manifest_sha256"],
        "r0_v2_manifest_sha256": contract["r0_v2"]["manifest_sha256"],
        "primary_control_plane_config_sha256": contract[
            "primary_control_plane"
        ]["config_sha256"],
        "primary_symbolic_operator_config_sha256": contract[
            "primary_symbolic_operator"
        ]["config_sha256"],
        "fusion_contract_sha256": canonical_sha256(contract["fusion"]),
        "frozen_primary_contract_sha256": config[
            "frozen_primary_contract"
        ]["contract_sha256"],
    }


def artifact_identity_context(
    config: Mapping[str, Any],
    *,
    condition: str,
    seed: int,
) -> dict[str, Any]:
    contract = config["frozen_primary_contract"]["contract"]
    system_a = contract["system_a"]
    scenario = contract["scenario"]
    return {
        "stage8_parent_evidence_commit": config["stage8_parent"]["evidence_commit"],
        "stage8_closure_commit": config["stage8_parent"]["closure_commit"],
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "condition_id": str(condition),
        "seed": int(seed),
        "runtime_identity_sha256": canonical_sha256(config["runtime"]),
        "scenario_manifest_canonical_sha256": scenario[
            "manifest_canonical_sha256"
        ],
        "preprocessing_state_hash": scenario["preprocessing_state_hash"],
        "system_a_manifest_sha256": system_a["manifest_sha256"],
        "system_a_checkpoint_sha256": system_a[
            "checkpoint_sha256_by_seed"
        ][str(seed)],
        "r0_v2_manifest_sha256": contract["r0_v2"]["manifest_sha256"],
        "primary_control_plane_config_sha256": contract[
            "primary_control_plane"
        ]["config_sha256"],
        "primary_symbolic_operator_config_sha256": contract[
            "primary_symbolic_operator"
        ]["config_sha256"],
        "fusion_contract_sha256": canonical_sha256(contract["fusion"]),
        "condition_spec_sha256": canonical_sha256(
            _condition_spec(config, condition)
        ),
        "frozen_primary_contract_sha256": config[
            "frozen_primary_contract"
        ]["contract_sha256"],
    }


def _condition_specs(
    *,
    baseline_required: bool,
    primary_contract_sha256: str,
) -> dict[str, Any]:
    primary = asdict(ControlPlaneConfig())

    def bind(
        spec: Mapping[str, Any],
        *,
        changed_factors: Sequence[str],
    ) -> dict[str, Any]:
        return {
            **dict(spec),
            "base_primary_contract_sha256": str(primary_contract_sha256),
            "changed_factors": list(changed_factors),
        }

    adaptive: dict[str, Any] = {
        "latency_0": bind(
            {
                "label_latency": 0,
                "detector_family": "adwin",
                "detector_signal": "hard_error",
                "replay_enabled": True,
            },
            changed_factors=("label_latency",),
        ),
        "latency_10000": bind(
            {
                "label_latency": 10000,
                "detector_family": "adwin",
                "detector_signal": "hard_error",
                "replay_enabled": True,
            },
            changed_factors=("label_latency",),
        ),
        "page_hinkley_hard_error": bind(
            {
                "label_latency": primary["label_latency"],
                "detector_family": "page_hinkley",
                "detector_signal": "hard_error",
                "detector_config": dict(PAGE_HINKLEY_CONFIG),
                "replay_enabled": True,
            },
            changed_factors=("detector_family",),
        ),
        "adwin_brier": bind(
            {
                "label_latency": primary["label_latency"],
                "detector_family": "adwin",
                "detector_signal": "brier",
                "detector_config": dict(ADWIN_CONFIG),
                "replay_enabled": True,
            },
            changed_factors=("detector_signal",),
        ),
        "no_replay": bind(
            {
                "label_latency": primary["label_latency"],
                "detector_family": "adwin",
                "detector_signal": "hard_error",
                "replay_enabled": False,
            },
            changed_factors=("replay_training_rows",),
        ),
    }
    if baseline_required:
        adaptive = {
            MATCHED_BASELINE_CONDITION: bind(
                {
                    "label_latency": primary["label_latency"],
                    "detector_family": "adwin",
                    "detector_signal": "hard_error",
                    "replay_enabled": True,
                },
                changed_factors=(),
            ),
            **adaptive,
        }
    return {
        "offline": {
            "lambda_0_7": bind(
                {"neural_weight": 0.70, "source": "frozen_stage8_trace"},
                changed_factors=("fusion_neural_weight",),
            ),
            "lambda_0_9": bind(
                {"neural_weight": 0.90, "source": "frozen_stage8_trace"},
                changed_factors=("fusion_neural_weight",),
            ),
            "lambda_1_0": bind(
                {"neural_weight": 1.00, "source": "frozen_stage8_trace"},
                changed_factors=("fusion_neural_weight",),
            ),
            "window_2500": bind(
                {
                    "reporting_window_rows": 2500,
                    "source": "frozen_stage8_trace",
                },
                changed_factors=("reporting_window_rows",),
            ),
            "window_10000": bind(
                {
                    "reporting_window_rows": 10000,
                    "source": "frozen_stage8_trace",
                },
                changed_factors=("reporting_window_rows",),
            ),
        },
        "symbolic_gate": {
            "static_symbolic_gate": bind(
                dict(STATIC_GATE_CONFIG),
                changed_factors=("symbolic_acceptance_gate",),
            ),
        },
        "adaptive": adaptive,
    }


def build_stage9_config() -> dict[str, Any]:
    _require_clean_for_preparation()
    _require_stage8_closure_ancestor()
    _require_no_stage9_outputs_before_preparation()
    parent = _verify_stage8_parent()
    primary_contract = _stage8_frozen_primary_contract()
    requirements = _requirements_identity()
    runtime = _runtime_inventory()
    primary_runtime = _primary_runtime_reference()
    baseline_required = _runtime_requires_matched_baseline(
        runtime, primary_runtime, requirements
    )
    source_hashes = _text_hashes(STAGE9_SOURCE_PATHS)
    source_commit = _git_output("rev-parse", "HEAD")

    payload: dict[str, Any] = {
        "schema_version": STAGE9_SCHEMA_VERSION,
        "run_id": STAGE9_RUN_ID,
        "status": "frozen_before_stage9_robustness_access",
        "prepared_from_git_commit": source_commit,
        "stage8_parent": {
            "evidence_commit": STAGE8_PARENT_EVIDENCE_COMMIT,
            "closure_commit": STAGE8_CLOSURE_COMMIT,
            **parent,
        },
        "frozen_primary_contract": primary_contract,
        "protocol": {
            "path": STAGE9_PROTOCOL_PATH,
            "sha256": source_hashes[STAGE9_PROTOCOL_PATH],
        },
        "scientific_source_hashes": source_hashes,
        "scientific_source_tree_sha256": canonical_sha256(source_hashes),
        "requirements": requirements,
        "runtime": runtime,
        "primary_runtime_reference": primary_runtime,
        "matched_baseline_required": baseline_required,
        "conditions": _condition_specs(
            baseline_required=baseline_required,
            primary_contract_sha256=primary_contract["contract_sha256"],
        ),
        "seeds": list(PRIMARY_SEEDS),
        "scenario": {
            "scenario_id": "cicids2017_sudden_benign_v1",
            "stream_rows": 138530,
            "boundary_index": 69260,
            "pre_reference_rows": 69260,
            "post_reference_rows": 69270,
            "boundary_role": "offline_scoring_and_diagnostics_only",
            "boundary_visibility_to_adaptive_runner": False,
            "random_reshuffle_allowed": False,
        },
        "analysis": {
            "classification": "prespecified_robustness_no_new_confirmatory_family",
            "inferential_unit": "matched_seed_within_fixed_primary_scenario",
            "all_five_seeds_required": True,
            "early_stop_for_outcome_direction_forbidden": True,
            "stage8_primary_replacement_forbidden": True,
        },
        "execution": {
            "heavy_root": "artifacts/cd_robustness_v1",
            "compact_root": "results/frozen/cd_robustness_v1",
            "write_once": True,
            "config_only_freeze_commit_required": True,
            "exact_head_ci_required_before_adaptive_access": True,
        },
        "stage9_outcomes_accessed_during_preparation": False,
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


def write_stage9_config() -> dict[str, Any]:
    payload = build_stage9_config()
    write_json_new(STAGE9_CONFIG_PATH, payload)
    return payload


def load_stage9_config() -> dict[str, Any]:
    payload = _read_json(STAGE9_CONFIG_PATH)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and stored_payload != canonical_sha256(payload):
        raise ValueError("Stage-9 config writer payload hash mismatch.")
    stored = payload.get("manifest_sha256")
    core = dict(payload)
    core.pop("manifest_sha256", None)
    if stored != canonical_sha256(core):
        raise ValueError("Stage-9 config canonical manifest hash mismatch.")
    return payload


def _require_config_only_freeze(config: Mapping[str, Any]) -> None:
    head = _git_output("rev-parse", "HEAD")
    changed = _git_output(
        "diff-tree", "--no-commit-id", "--name-only", "-r", head
    ).splitlines()
    parents = _git_output("show", "-s", "--format=%P", head).split()
    if len(parents) != 1:
        raise ValueError("Stage-9 config freeze commit must have exactly one parent.")
    if parents[0] != config["prepared_from_git_commit"]:
        raise ValueError("Stage-9 config freeze parent does not match preparation head.")
    expected = STAGE9_CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix()
    if changed != [expected]:
        raise ValueError("Stage-9 config freeze commit must contain only the config.")


def verify_stage9_config_for_execution(
    *,
    allow_untracked_compact_output: bool = False,
) -> dict[str, Any]:
    status = _git_output("status", "--porcelain")
    if status:
        lines = [line for line in status.splitlines() if line.strip()]
        allowed = (
            allow_untracked_compact_output
            and lines
            and all(
                line.startswith("?? results/frozen/cd_robustness_v1/")
                for line in lines
            )
        )
        if not allowed:
            raise RuntimeError(
                "Stage-9 execution requires a clean worktree; compact verification "
                "may allow only untracked Stage-9 compact output."
            )
    config = load_stage9_config()
    head = _git_output("rev-parse", "HEAD")
    if head != _git_output(
        "log",
        "-n",
        "1",
        "--format=%H",
        "--",
        STAGE9_CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix(),
    ):
        raise ValueError("Stage-9 execution requires exact config-freeze HEAD.")
    _require_config_only_freeze(config)
    if config["stage9_outcomes_accessed_during_preparation"] is not False:
        raise ValueError("Stage-9 preparation outcome-access invariant failed.")
    if config["stage8_parent"] != {
        "evidence_commit": STAGE8_PARENT_EVIDENCE_COMMIT,
        "closure_commit": STAGE8_CLOSURE_COMMIT,
        **_verify_stage8_parent(),
    }:
        raise ValueError("Stage-8 parent evidence changed.")
    if config["frozen_primary_contract"] != _stage8_frozen_primary_contract():
        raise ValueError("Frozen Stage-8 primary treatment contract changed.")
    current_hashes = _text_hashes(STAGE9_SOURCE_PATHS)
    if current_hashes != config["scientific_source_hashes"]:
        raise ValueError("Stage-9 scientific source identity changed.")
    if _requirements_identity() != config["requirements"]:
        raise ValueError("Stage-9 dependency identity changed.")
    if _runtime_inventory() != config["runtime"]:
        raise ValueError("Stage-9 runtime identity changed.")
    return config


def main() -> None:
    payload = write_stage9_config()
    print(
        json.dumps(
            {
                "status": "stage9_config_written",
                "path": STAGE9_CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "manifest_sha256": payload["manifest_sha256"],
                "prepared_from_git_commit": payload["prepared_from_git_commit"],
                "matched_baseline_required": payload["matched_baseline_required"],
                "stage9_outcomes_accessed_during_preparation": False,
                "next_gate": "commit only config and require exact-head CI",
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
