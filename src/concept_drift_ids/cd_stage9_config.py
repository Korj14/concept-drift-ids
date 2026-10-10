from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from concept_drift_ids.cd_control_plane import ADWIN_CONFIG, canonical_sha256, write_json_new
from concept_drift_ids.cd_runtime import (
    PRIMARY_THREAD_ENV,
    configure_torch_primary_runtime,
)
from concept_drift_ids.cd_symbolic_arms import SymbolicOperatorConfig
from concept_drift_ids.cd_symbolic_lifecycle import OnlineRuleGate
from concept_drift_ids.scenario_manifest import sha256_normalized_text


PROJECT_ROOT = Path(__file__).resolve().parents[2]

STAGE9_RUN_ID = "cd-robustness-v1"
STAGE9_CONFIG_PATH = PROJECT_ROOT / "data" / "manifests" / "cd_stage9_run_config_v1.json"
STAGE9_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "cd_robustness_v1"
STAGE9_COMPACT_ROOT = PROJECT_ROOT / "results" / "frozen" / "cd_robustness_v1"

PARENT_EVIDENCE_COMMIT = "c2ded83b8195b9321e715626c1f305f9627936e8"
PARENT_COMPACT_EXPORT_MANIFEST_SHA256 = (
    "409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523"
)
PARENT_CONFIRMATORY_AGGREGATE_SHA256 = (
    "1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d"
)
PARENT_PRIMARY_CORRECTED_CONFIG_MANIFEST_SHA256 = (
    "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222"
)
PARENT_MECHANISM_ARCHIVE_COMMIT = "90e574fd3cee278fd4514609c24dfe58d5c6d944"
PARENT_MECHANISM_AGGREGATE_SHA256 = (
    "6c35c026c52fa7bee93cd31bffa459b2bf605efe950f9645e6bea48f86a99acd"
)

PRIMARY_COMPACT_ROOT = PROJECT_ROOT / "results" / "frozen" / "cd_primary_v1"
PRIMARY_CONFIG_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "cd_primary_run_config_v1_1.json"
)
PRIMARY_RUNTIME_MANIFEST_PATH = (
    PRIMARY_COMPACT_ROOT
    / "phase_a_shared_control_plane"
    / "seed-0"
    / "run_manifest.json"
)
PRIMARY_CONFIRMATORY_PATH = (
    PRIMARY_COMPACT_ROOT
    / "phase_c_offline_evaluation_v1_1"
    / "confirmatory_analysis.json"
)
PRIMARY_COMPACT_MANIFEST_PATH = PRIMARY_COMPACT_ROOT / "compact_export_manifest.json"

STAGE9_PROTOCOL_PATH = "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md"
STAGE9_IMPLEMENTATION_FREEZE_PATH = "STAGE9_IMPLEMENTATION_FREEZE.md"

PRIMARY_SEEDS = (0, 1, 2, 3, 4)
PRIMARY_BOUNDARY_INDEX = 69_260
PRIMARY_STREAM_ROWS = 138_530

PAGE_HINKLEY_CONFIG = {
    "min_instances": 30,
    "delta": 0.005,
    "threshold": 50.0,
    "alpha": 0.9999,
    "mode": "both",
}

STATIC_GATE = OnlineRuleGate(
    min_support=0.001,
    min_covered=100,
    min_class_precision=0.80,
    min_precision_lcb=0.0,
    min_neural_fidelity=0.90,
    min_fidelity_lcb=0.0,
    min_stability=0.90,
    max_complexity=4,
    bootstrap_replicates=100,
)
STATIC_OPERATOR = SymbolicOperatorConfig(gate=STATIC_GATE)

CONDITIONS: dict[str, dict[str, Any]] = {
    "O_LAMBDA_070": {
        "group": "offline",
        "kind": "fusion_weight",
        "neural_weight": 0.70,
        "adaptive_rerun": False,
        "threshold_refit": False,
    },
    "O_LAMBDA_090": {
        "group": "offline",
        "kind": "fusion_weight",
        "neural_weight": 0.90,
        "adaptive_rerun": False,
        "threshold_refit": False,
    },
    "O_LAMBDA_100": {
        "group": "offline",
        "kind": "fusion_weight",
        "neural_weight": 1.00,
        "adaptive_rerun": False,
        "threshold_refit": False,
        "role": "neural_only_negative_control",
    },
    "O_WINDOW_2500": {
        "group": "offline",
        "kind": "reporting_window",
        "window_rows": 2_500,
        "adaptive_rerun": False,
        "whole_post_endpoint_unchanged": True,
    },
    "O_WINDOW_10000": {
        "group": "offline",
        "kind": "reporting_window",
        "window_rows": 10_000,
        "adaptive_rerun": False,
        "whole_post_endpoint_unchanged": True,
    },
    "G_STATIC_GATE": {
        "group": "symbolic_gate",
        "kind": "static_style_symbolic_gate",
        "reuse_primary_phase_a": True,
        "operator_config_sha256": STATIC_OPERATOR.sha256(),
        "gate": {
            "min_support": 0.001,
            "min_covered": 100,
            "min_class_precision": 0.80,
            "min_neural_fidelity": 0.90,
            "bootstrap_replicates": 100,
            "min_stability": 0.90,
            "max_complexity": 4,
            "wilson_lcb_required": False,
            "min_precision_lcb": 0.0,
            "min_fidelity_lcb": 0.0,
        },
    },
    "A_BASELINE": {
        "group": "adaptive",
        "kind": "matched_primary_runtime_baseline",
        "label_latency": 5_000,
        "detector": "adwin_hard_error",
        "replay": "primary",
    },
    "A_LATENCY_0": {
        "group": "adaptive",
        "kind": "label_latency",
        "label_latency": 0,
        "detector": "adwin_hard_error",
        "replay": "primary",
    },
    "A_LATENCY_10000": {
        "group": "adaptive",
        "kind": "label_latency",
        "label_latency": 10_000,
        "detector": "adwin_hard_error",
        "replay": "primary",
    },
    "A_PAGE_HINKLEY": {
        "group": "adaptive",
        "kind": "detector_family",
        "label_latency": 5_000,
        "detector": "page_hinkley_hard_error",
        "page_hinkley": PAGE_HINKLEY_CONFIG,
        "replay": "primary",
    },
    "A_ADWIN_BRIER": {
        "group": "adaptive",
        "kind": "detector_signal",
        "label_latency": 5_000,
        "detector": "adwin_brier",
        "adwin": dict(ADWIN_CONFIG),
        "replay": "primary",
    },
    "A_NO_REPLAY": {
        "group": "adaptive",
        "kind": "neural_replay_ablation",
        "label_latency": 5_000,
        "detector": "adwin_hard_error",
        "replay": "none",
        "replay_anchor_rows": 0,
        "replay_online_rows": 0,
    },
}

SCIENTIFIC_SOURCE_PATHS = (
    ".gitattributes",
    ".gitignore",
    ".github/workflows/stage3-unit.yml",
    "requirements-lock.txt",
    "tests/test_cd_stage9_unit.py",
    "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md",
    "STAGE9_IMPLEMENTATION_FREEZE.md",
    "src/concept_drift_ids/cd_stage9_config.py",
    "src/concept_drift_ids/cd_stage9_control_plane.py",
    "src/concept_drift_ids/cd_stage9_phase_a.py",
    "src/concept_drift_ids/cd_stage9_symbolic.py",
    "src/concept_drift_ids/cd_stage9_evaluation.py",
    "src/concept_drift_ids/cd_stage9_export.py",
    "src/concept_drift_ids/cd_control_plane.py",
    "src/concept_drift_ids/cd_evidence.py",
    "src/concept_drift_ids/cd_primary_adapter.py",
    "src/concept_drift_ids/cd_primary_phase_a.py",
    "src/concept_drift_ids/cd_primary_phase_b.py",
    "src/concept_drift_ids/cd_r0_lifecycle.py",
    "src/concept_drift_ids/cd_runtime.py",
    "src/concept_drift_ids/cd_shared_runner.py",
    "src/concept_drift_ids/cd_symbolic_arms.py",
    "src/concept_drift_ids/cd_symbolic_lifecycle.py",
    "src/concept_drift_ids/cd_symbolic_runner.py",
    "src/concept_drift_ids/frozen_preprocessing.py",
    "src/concept_drift_ids/neural.py",
    "src/concept_drift_ids/scenario_manifest.py",
    "src/concept_drift_ids/system_a.py",
    "scripts/run_stage9.ps1",
    "stage9.py",
)


def _git(*args: str, project_root: Path = PROJECT_ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=check,
        capture_output=True,
        text=True,
    )


def _git_output(*args: str, project_root: Path = PROJECT_ROOT) -> str:
    return _git(*args, project_root=project_root).stdout.strip()


def _require_clean_worktree(*, project_root: Path = PROJECT_ROOT) -> None:
    status = _git_output("status", "--porcelain", project_root=project_root)
    if status:
        raise RuntimeError(f"Stage-9 preparation/execution requires a clean worktree: {status}")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_verified_canonical_json(
    path: Path,
    *,
    manifest_key: str,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    payload = _read_json(path)
    stored = payload.get(manifest_key)
    core = dict(payload)
    core.pop(manifest_key, None)
    core.pop("payload_sha256", None)
    if stored != canonical_sha256(core):
        raise ValueError(f"Canonical identity mismatch: {path}")
    if stored != expected_manifest_sha256:
        raise ValueError(f"Unexpected frozen identity: {path}")
    return payload


def _verify_parent_compact_evidence() -> dict[str, Any]:
    manifest = _read_verified_canonical_json(
        PRIMARY_COMPACT_MANIFEST_PATH,
        manifest_key="manifest_sha256",
        expected_manifest_sha256=PARENT_COMPACT_EXPORT_MANIFEST_SHA256,
    )
    confirmatory = _read_json(PRIMARY_CONFIRMATORY_PATH)
    stored = confirmatory.get("confirmatory_analysis_sha256")
    if stored is None:
        stored = confirmatory.get("manifest_sha256")
    core = dict(confirmatory)
    core.pop("confirmatory_analysis_sha256", None)
    core.pop("manifest_sha256", None)
    core.pop("payload_sha256", None)
    if stored != canonical_sha256(core):
        raise ValueError("Primary confirmatory aggregate canonical hash mismatch.")
    if stored != PARENT_CONFIRMATORY_AGGREGATE_SHA256:
        raise ValueError("Unexpected primary confirmatory aggregate identity.")
    return {
        "compact_export_manifest_sha256": manifest["manifest_sha256"],
        "confirmatory_aggregate_sha256": stored,
    }


def _verify_parent_primary_config() -> dict[str, Any]:
    payload = _read_verified_canonical_json(
        PRIMARY_CONFIG_PATH,
        manifest_key="manifest_sha256",
        expected_manifest_sha256=PARENT_PRIMARY_CORRECTED_CONFIG_MANIFEST_SHA256,
    )
    scenario = payload["scenario"]
    if int(scenario["stream_rows"]) != PRIMARY_STREAM_ROWS:
        raise ValueError("Primary stream length changed.")
    if scenario["scenario_id"] != "cicids2017_sudden_benign_v1":
        raise ValueError("Primary scenario identity changed.")
    return payload


def _source_hashes(*, project_root: Path = PROJECT_ROOT) -> dict[str, str]:
    out: dict[str, str] = {}
    for relative in SCIENTIFIC_SOURCE_PATHS:
        path = project_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Missing Stage-9 scientific source: {relative}")
        out[relative] = sha256_normalized_text(path)
    return out


def _source_tree_sha256(hashes: Mapping[str, str]) -> str:
    return canonical_sha256(dict(sorted(hashes.items())))


def _normalized_threadpool(runtime: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in runtime.get("threadpool_info", []):
        rows.append(
            {
                key: item.get(key)
                for key in (
                    "user_api",
                    "internal_api",
                    "prefix",
                    "version",
                    "num_threads",
                    "threading_layer",
                    "architecture",
                )
            }
        )
    rows.sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
    return rows


def _material_runtime_identity(runtime: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "platform": runtime.get("platform"),
        "processor": runtime.get("processor"),
        "python_implementation": runtime.get("python_implementation"),
        "python_version": runtime.get("python_version"),
        "locked_distributions_sha256": runtime.get("locked_distributions_sha256"),
        "torch_version": runtime.get("torch_version"),
        "torch_deterministic_algorithms": runtime.get("torch_deterministic_algorithms"),
        "torch_num_threads": runtime.get("torch_num_threads"),
        "torch_num_interop_threads": runtime.get("torch_num_interop_threads"),
        "thread_environment": runtime.get("thread_environment"),
        "threadpool_info": _normalized_threadpool(runtime),
    }


def _primary_runtime() -> dict[str, Any]:
    payload = _read_json(PRIMARY_RUNTIME_MANIFEST_PATH)
    runtime = payload["runtime"]
    if runtime["locked_distributions_sha256"] != (
        "8a928d5c9df8554f88ba80edd2918f5f6a18b382697f6f561dbe87a8ed9a0052"
    ):
        raise ValueError("Unexpected Stage-8 locked-distribution identity.")
    return runtime


def _current_runtime() -> dict[str, Any]:
    runtime = configure_torch_primary_runtime()
    if sys.version_info[:3] != (3, 11, 9):
        raise RuntimeError("Stage 9 requires Python 3.11.9 exactly.")
    for key, expected in PRIMARY_THREAD_ENV.items():
        if os.environ.get(key) != expected:
            raise RuntimeError(f"Stage-9 thread environment mismatch: {key}")
    return runtime


def _runtime_comparison(
    primary_runtime: Mapping[str, Any],
    stage9_runtime: Mapping[str, Any],
) -> dict[str, Any]:
    primary_material = _material_runtime_identity(primary_runtime)
    stage9_material = _material_runtime_identity(stage9_runtime)
    fields = sorted(set(primary_material) | set(stage9_material))
    mismatches = {
        key: {
            "stage8": primary_material.get(key),
            "stage9": stage9_material.get(key),
        }
        for key in fields
        if primary_material.get(key) != stage9_material.get(key)
    }
    return {
        "stage8_material_identity": primary_material,
        "stage9_material_identity": stage9_material,
        "materially_identical": not mismatches,
        "mismatches": mismatches,
        "matched_stage9_baseline_required": bool(mismatches),
    }


def _condition_payload(runtime_comparison: Mapping[str, Any]) -> dict[str, Any]:
    conditions = json.loads(json.dumps(CONDITIONS, sort_keys=True))
    conditions["A_BASELINE"]["required"] = bool(
        runtime_comparison["matched_stage9_baseline_required"]
    )
    for key, value in conditions.items():
        value["condition_id"] = key
        value["seeds"] = list(PRIMARY_SEEDS)
    return conditions


def build_stage9_config(*, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    _require_clean_worktree(project_root=project_root)
    parent = _verify_parent_compact_evidence()
    primary = _verify_parent_primary_config()

    source_commit = _git_output("rev-parse", "HEAD", project_root=project_root)
    source_hashes = _source_hashes(project_root=project_root)
    primary_runtime = _primary_runtime()
    stage9_runtime = _current_runtime()

    frozen_requirements = primary["requirements"]
    current_lock_identity = sha256_normalized_text(
        project_root / "requirements-lock.txt"
    )
    if current_lock_identity != frozen_requirements[
        "binding_normalized_text_sha256"
    ]:
        raise RuntimeError("Stage-9 requirements lock differs from frozen Stage 8.")
    if stage9_runtime["locked_distributions_sha256"] != frozen_requirements[
        "installed_distributions_sha256"
    ]:
        raise RuntimeError(
            "Stage-9 installed distribution identity differs from frozen Stage 8."
        )

    runtime_comparison = _runtime_comparison(primary_runtime, stage9_runtime)

    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "frozen_stage9_prespecified_robustness_pre_outcome",
        "run_id": STAGE9_RUN_ID,
        "source_commit": source_commit,
        "parent_stage8": {
            "evidence_commit": PARENT_EVIDENCE_COMMIT,
            "compact_export_manifest_sha256": parent[
                "compact_export_manifest_sha256"
            ],
            "confirmatory_aggregate_sha256": parent[
                "confirmatory_aggregate_sha256"
            ],
            "corrected_primary_config_manifest_sha256": (
                PARENT_PRIMARY_CORRECTED_CONFIG_MANIFEST_SHA256
            ),
            "mechanism_archive_commit": PARENT_MECHANISM_ARCHIVE_COMMIT,
            "mechanism_aggregate_sha256": PARENT_MECHANISM_AGGREGATE_SHA256,
            "mechanism_role": "context_only_not_condition_selection",
        },
        "scenario": {
            "scenario_id": primary["scenario"]["scenario_id"],
            "scenario_version": primary["scenario"]["scenario_version"],
            "manifest_canonical_sha256": primary["scenario"][
                "manifest_canonical_sha256"
            ],
            "preprocessing_state_hash": primary["scenario"][
                "preprocessing_state_hash"
            ],
            "boundary_index": PRIMARY_BOUNDARY_INDEX,
            "boundary_role": "offline_scoring_and_diagnostics_only",
            "stream_rows": PRIMARY_STREAM_ROWS,
        },
        "seeds": list(PRIMARY_SEEDS),
        "parent_primary_reference": {
            "primary_control_plane": primary["primary_control_plane"],
            "primary_symbolic_operator": primary["primary_symbolic_operator"],
            "fusion": primary["fusion"],
            "system_a": primary["system_a"],
            "r0_v2": primary["r0_v2"],
            "requirements": primary["requirements"],
        },
        "conditions": _condition_payload(runtime_comparison),
        "detectors": {
            "adwin": dict(ADWIN_CONFIG),
            "page_hinkley": dict(PAGE_HINKLEY_CONFIG),
            "page_hinkley_parameter_source": (
                "explicit River 0.26.1 constructor defaults; no Stage-8 trigger/outcome tuning"
            ),
        },
        "symbolic_static_gate": {
            "operator_config_sha256": STATIC_OPERATOR.sha256(),
            "gate": {
                "min_support": STATIC_GATE.min_support,
                "min_covered": STATIC_GATE.min_covered,
                "min_class_precision": STATIC_GATE.min_class_precision,
                "min_precision_lcb": STATIC_GATE.min_precision_lcb,
                "min_neural_fidelity": STATIC_GATE.min_neural_fidelity,
                "min_fidelity_lcb": STATIC_GATE.min_fidelity_lcb,
                "min_stability": STATIC_GATE.min_stability,
                "max_complexity": STATIC_GATE.max_complexity,
                "bootstrap_replicates": STATIC_GATE.bootstrap_replicates,
                "wilson_lcb_required": False,
            },
        },
        "runtime": {
            "stage8": primary_runtime,
            "stage9": stage9_runtime,
            "comparison": runtime_comparison,
        },
        "execution": {
            "heavy_output_root": "artifacts/cd_robustness_v1",
            "compact_output_root": "results/frozen/cd_robustness_v1",
            "write_once": True,
            "config_only_freeze_commit_required": True,
            "exact_config_head_required": True,
            "all_five_seeds_required": True,
            "stage8_files_overwritten": False,
        },
        "preparation": {
            "primary_partitions_loaded": False,
            "heavy_phase_c_traces_loaded": False,
            "stage9_treatment_executed": False,
            "stage9_outcome_accessed": False,
        },
        "protocol": {
            "path": STAGE9_PROTOCOL_PATH,
            "sha256": sha256_normalized_text(project_root / STAGE9_PROTOCOL_PATH),
            "hash_semantics": "utf8_text_crlf_lf_normalized",
        },
        "implementation_freeze": {
            "path": STAGE9_IMPLEMENTATION_FREEZE_PATH,
            "sha256": sha256_normalized_text(
                project_root / STAGE9_IMPLEMENTATION_FREEZE_PATH
            ),
            "hash_semantics": "utf8_text_crlf_lf_normalized",
        },
        "scientific_source_hashes": source_hashes,
        "scientific_source_tree_sha256": _source_tree_sha256(source_hashes),
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


def write_stage9_config(
    *,
    path: Path = STAGE9_CONFIG_PATH,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Stage-9 config: {path}")
    payload = build_stage9_config(project_root=project_root)
    write_json_new(path, payload)
    return payload


def load_stage9_config(*, path: Path = STAGE9_CONFIG_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            "Stage-9 config is absent. Run stage9.py prepare and freeze the generated config."
        )
    payload = _read_json(path)
    stored = payload.get("manifest_sha256")
    core = dict(payload)
    core.pop("manifest_sha256", None)
    core.pop("payload_sha256", None)
    if stored != canonical_sha256(core):
        raise ValueError("Stage-9 config canonical hash mismatch.")
    return payload


def _require_config_tracked(*, project_root: Path = PROJECT_ROOT) -> None:
    result = _git(
        "ls-files",
        "--error-unmatch",
        "data/manifests/cd_stage9_run_config_v1.json",
        project_root=project_root,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Stage-9 config must be committed before execution.")


def _require_exact_config_commit(
    config: Mapping[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> str:
    head = _git_output("rev-parse", "HEAD", project_root=project_root)
    config_commit = _git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        "data/manifests/cd_stage9_run_config_v1.json",
        project_root=project_root,
    )
    if not config_commit or head != config_commit:
        raise RuntimeError(
            "Stage-9 execution requires HEAD to equal the config-freeze commit exactly."
        )
    parents = _git_output(
        "show",
        "-s",
        "--format=%P",
        "HEAD",
        project_root=project_root,
    ).split()
    if parents != [str(config["source_commit"])]:
        raise RuntimeError(
            "Stage-9 config-freeze commit must have exactly one parent equal to the source head."
        )
    changed = tuple(
        line.strip()
        for line in _git_output(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
            project_root=project_root,
        ).splitlines()
        if line.strip()
    )
    expected = ("data/manifests/cd_stage9_run_config_v1.json",)
    if changed != expected:
        raise RuntimeError(
            "Stage-9 config freeze commit must change exactly the Stage-9 config file. "
            f"Observed: {changed}"
        )
    return head


def verify_stage9_config_repository_contract(
    *,
    project_root: Path = PROJECT_ROOT,
    require_clean: bool = True,
) -> dict[str, Any]:
    if require_clean:
        _require_clean_worktree(project_root=project_root)
    _require_config_tracked(project_root=project_root)
    config = load_stage9_config(
        path=project_root / "data" / "manifests" / "cd_stage9_run_config_v1.json"
    )
    _require_exact_config_commit(config, project_root=project_root)

    parent = _verify_parent_compact_evidence()
    if config["parent_stage8"]["evidence_commit"] != PARENT_EVIDENCE_COMMIT:
        raise ValueError("Stage-9 parent evidence commit changed.")
    if config["parent_stage8"]["compact_export_manifest_sha256"] != parent[
        "compact_export_manifest_sha256"
    ]:
        raise ValueError("Stage-9 parent compact manifest changed.")
    if config["parent_stage8"]["confirmatory_aggregate_sha256"] != parent[
        "confirmatory_aggregate_sha256"
    ]:
        raise ValueError("Stage-9 parent confirmatory aggregate changed.")

    primary = _verify_parent_primary_config()
    expected_primary_reference = {
        "primary_control_plane": primary["primary_control_plane"],
        "primary_symbolic_operator": primary["primary_symbolic_operator"],
        "fusion": primary["fusion"],
        "system_a": primary["system_a"],
        "r0_v2": primary["r0_v2"],
        "requirements": primary["requirements"],
    }
    if config["parent_primary_reference"] != expected_primary_reference:
        raise ValueError("Stage-9 parent primary control identities changed.")

    if sha256_normalized_text(
        project_root / "requirements-lock.txt"
    ) != primary["requirements"]["binding_normalized_text_sha256"]:
        raise ValueError("Stage-9 frozen dependency lock identity changed.")

    if tuple(config["seeds"]) != PRIMARY_SEEDS:
        raise ValueError("Stage-9 seed set changed.")
    if int(config["scenario"]["boundary_index"]) != PRIMARY_BOUNDARY_INDEX:
        raise ValueError("Stage-9 boundary index changed.")
    if config["scenario"]["boundary_role"] != "offline_scoring_and_diagnostics_only":
        raise ValueError("Stage-9 boundary role changed.")
    if int(config["scenario"]["stream_rows"]) != PRIMARY_STREAM_ROWS:
        raise ValueError("Stage-9 stream length changed.")

    expected_conditions = _condition_payload(config["runtime"]["comparison"])
    if config["conditions"] != expected_conditions:
        raise ValueError("Stage-9 condition definitions changed.")
    if config["detectors"]["page_hinkley"] != PAGE_HINKLEY_CONFIG:
        raise ValueError("Stage-9 Page-Hinkley configuration changed.")
    if config["detectors"]["adwin"] != ADWIN_CONFIG:
        raise ValueError("Stage-9 ADWIN configuration changed.")
    if config["symbolic_static_gate"]["operator_config_sha256"] != STATIC_OPERATOR.sha256():
        raise ValueError("Stage-9 static-gate operator identity changed.")

    current_hashes = _source_hashes(project_root=project_root)
    if current_hashes != config["scientific_source_hashes"]:
        raise ValueError("Stage-9 scientific source hash set changed.")
    if _source_tree_sha256(current_hashes) != config["scientific_source_tree_sha256"]:
        raise ValueError("Stage-9 scientific source tree identity changed.")

    recomputed_runtime_comparison = _runtime_comparison(
        config["runtime"]["stage8"],
        config["runtime"]["stage9"],
    )
    if recomputed_runtime_comparison != config["runtime"]["comparison"]:
        raise ValueError("Frozen Stage-9 runtime comparison is internally inconsistent.")

    if config["preparation"] != {
        "primary_partitions_loaded": False,
        "heavy_phase_c_traces_loaded": False,
        "stage9_treatment_executed": False,
        "stage9_outcome_accessed": False,
    }:
        raise ValueError("Stage-9 preparation provenance changed.")

    return config


def verify_stage9_config_for_execution(
    *,
    project_root: Path = PROJECT_ROOT,
    require_clean: bool = True,
) -> dict[str, Any]:
    config = verify_stage9_config_repository_contract(
        project_root=project_root,
        require_clean=require_clean,
    )
    runtime = _current_runtime()
    material = _material_runtime_identity(runtime)
    if material != config["runtime"]["comparison"]["stage9_material_identity"]:
        raise RuntimeError("Active Stage-9 runtime differs from frozen config.")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or verify the Stage-9 robustness config.")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--repository-contract", action="store_true")
    args = parser.parse_args()

    if args.verify or args.repository_contract:
        payload = (
            verify_stage9_config_repository_contract()
            if args.repository_contract
            else verify_stage9_config_for_execution()
        )
        print(
            json.dumps(
                {
                    "status": (
                        "stage9_config_verified_repository_contract"
                        if args.repository_contract
                        else "stage9_config_verified_for_execution"
                    ),
                    "manifest_sha256": payload["manifest_sha256"],
                    "source_commit": payload["source_commit"],
                    "matched_stage9_baseline_required": payload["runtime"]["comparison"][
                        "matched_stage9_baseline_required"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    payload = write_stage9_config()
    print(
        json.dumps(
            {
                "status": "stage9_config_written_pre_outcome",
                "path": STAGE9_CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "manifest_sha256": payload["manifest_sha256"],
                "source_commit": payload["source_commit"],
                "matched_stage9_baseline_required": payload["runtime"]["comparison"][
                    "matched_stage9_baseline_required"
                ],
                "primary_partitions_loaded": False,
                "heavy_phase_c_traces_loaded": False,
                "stage9_outcome_accessed": False,
                "next_gate": "commit only the Stage-9 config and require exact-head CI",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
