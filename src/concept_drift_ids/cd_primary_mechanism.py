from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from sklearn.metrics import matthews_corrcoef

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_implementation_preflight import PROJECT_ROOT
from concept_drift_ids.cd_primary_config import (
    _git,
    _git_output,
    require_clean_worktree,
)
from concept_drift_ids.scenario_manifest import sha256_file


PARENT_EVIDENCE_COMMIT = "c2ded83b8195b9321e715626c1f305f9627936e8"
PARENT_COMPACT_EXPORT_MANIFEST_SHA256 = (
    "409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523"
)
PARENT_CONFIRMATORY_AGGREGATE_SHA256 = (
    "1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d"
)
PROTOCOL_PATH = "STAGE8_SYMBOLIC_VALUE_MECHANISM_AUDIT_PROTOCOL.md"
CONFIG_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "cd_primary_mechanism_audit_v1.json"
)
COMPACT_ROOT = PROJECT_ROOT / "results" / "frozen" / "cd_primary_v1"
HEAVY_PHASE_C_ROOT = (
    PROJECT_ROOT
    / "artifacts"
    / "cd_primary_v1"
    / "phase_c_offline_evaluation_v1_1"
)
OUTPUT_ROOT = PROJECT_ROOT / "results" / "frozen" / "cd_primary_mechanism_v1"
BOUNDARY_INDEX = 69_260
STREAM_ROWS = 138_530
SEEDS = (0, 1, 2, 3, 4)
TARGET_ARMS = ("d_drift", "d_periodic")
MECHANISMS = ("withdrawal", "addition", "retained_authority")
DOMAINS = ("pre", "post")
PRIMARY_DECISION_KEY = "decision_lambda_0_5"
LAMBDA_ONE_DECISION_KEY = "decision_lambda_1_0"
LAMBDA_ONE_SCORE_KEY = "fused_probability_lambda_1_0"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_verified_json(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError(f"JSON payload hash mismatch: {path}")
    return payload


def _verify_parent_compact_evidence() -> dict[str, Any]:
    manifest = _read_verified_json(COMPACT_ROOT / "compact_export_manifest.json")
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError("Parent compact-export manifest canonical hash mismatch.")
    if stored != PARENT_COMPACT_EXPORT_MANIFEST_SHA256:
        raise ValueError("Unexpected parent compact-export manifest identity.")

    confirmatory = _read_verified_json(
        COMPACT_ROOT
        / "phase_c_offline_evaluation_v1_1"
        / "confirmatory_analysis.json"
    )
    stored_confirmatory = confirmatory.pop("manifest_sha256", None)
    if stored_confirmatory != canonical_sha256(confirmatory):
        raise ValueError("Parent confirmatory aggregate canonical hash mismatch.")
    if stored_confirmatory != PARENT_CONFIRMATORY_AGGREGATE_SHA256:
        raise ValueError("Unexpected parent confirmatory aggregate identity.")
    return {
        "compact_export_manifest_sha256": stored,
        "confirmatory_aggregate_sha256": stored_confirmatory,
    }



def build_mechanism_config() -> dict[str, Any]:
    """Freeze the post-primary mechanism audit without reading row-level traces."""
    require_clean_worktree(project_root=PROJECT_ROOT)
    parent = _verify_parent_compact_evidence()
    source_commit = _git_output("rev-parse", "HEAD", project_root=PROJECT_ROOT)
    protocol_file = PROJECT_ROOT / PROTOCOL_PATH
    source_file = PROJECT_ROOT / "src" / "concept_drift_ids" / "cd_primary_mechanism.py"
    runner_file = PROJECT_ROOT / "run.py"
    tests_file = PROJECT_ROOT / "tests" / "test_cd_primary_mechanism_unit.py"
    for path in (protocol_file, source_file, runner_file, tests_file):
        if not path.is_file():
            raise FileNotFoundError(f"Missing mechanism-audit source: {path}")

    payload = {
        "schema_version": 1,
        "status": "frozen_post_primary_before_row_level_mechanism_trace_access",
        "source_commit": source_commit,
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "parent_compact_export_manifest_sha256": parent[
            "compact_export_manifest_sha256"
        ],
        "parent_confirmatory_aggregate_sha256": parent[
            "confirmatory_aggregate_sha256"
        ],
        "protocol_path": PROTOCOL_PATH,
        "protocol_sha256": sha256_file(protocol_file),
        "source_sha256": sha256_file(source_file),
        "runner_sha256": sha256_file(runner_file),
        "tests_sha256": sha256_file(tests_file),
        "seeds": list(SEEDS),
        "target_arms": list(TARGET_ARMS),
        "mechanisms": list(MECHANISMS),
        "domains": list(DOMAINS),
        "boundary_index": BOUNDARY_INDEX,
        "stream_rows": STREAM_ROWS,
        "primary_decision_key": PRIMARY_DECISION_KEY,
        "lambda_one_decision_key": LAMBDA_ONE_DECISION_KEY,
        "lambda_one_score_key": LAMBDA_ONE_SCORE_KEY,
        "row_level_mechanism_trace_accessed_during_preparation": False,
        "analysis_classification": (
            "exploratory_descriptive_post_primary_no_new_pvalue_family"
        ),
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


def write_mechanism_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        raise FileExistsError(
            f"Refusing to overwrite mechanism-audit config: {CONFIG_PATH}"
        )
    payload = build_mechanism_config()
    write_json_new(CONFIG_PATH, payload)
    return payload


def load_mechanism_config() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            "Mechanism-audit config is absent. Commit the frozen v1 config "
            "before executing the mechanism audit."
        )
    payload = _read_json(CONFIG_PATH)
    stored_payload = payload.pop("payload_sha256", None)
    stored_manifest = payload.get("manifest_sha256")
    core = dict(payload)
    core.pop("manifest_sha256", None)
    if stored_manifest != canonical_sha256(core):
        raise ValueError("Mechanism-audit config manifest hash mismatch.")
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError("Mechanism-audit config writer hash mismatch.")
    return payload


def _require_no_tracked_worktree_changes() -> None:
    status = _git_output(
        "status",
        "--porcelain",
        "--untracked-files=no",
        project_root=PROJECT_ROOT,
    )
    if status:
        raise RuntimeError(
            "Mechanism audit refuses tracked worktree/index changes."
        )


def verify_mechanism_config_for_execution(
    *,
    require_fully_clean: bool = True,
) -> dict[str, Any]:
    if require_fully_clean:
        require_clean_worktree(project_root=PROJECT_ROOT)
    else:
        _require_no_tracked_worktree_changes()
    config = load_mechanism_config()
    relative = CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix()

    tracked = _git(
        "ls-files",
        "--error-unmatch",
        relative,
        project_root=PROJECT_ROOT,
        check=False,
    )
    if tracked.returncode != 0:
        raise RuntimeError("Mechanism-audit config must be committed before execution.")

    head = _git_output("rev-parse", "HEAD", project_root=PROJECT_ROOT)
    config_commit = _git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        relative,
        project_root=PROJECT_ROOT,
    )
    if head != config_commit:
        raise RuntimeError(
            "Mechanism audit requires HEAD to be exactly the config freeze commit."
        )
    parent = _git_output("rev-parse", "HEAD^", project_root=PROJECT_ROOT)
    if parent != str(config["source_commit"]):
        raise RuntimeError(
            "Mechanism-audit config commit parent differs from frozen source commit."
        )
    changed = tuple(
        line.strip()
        for line in _git_output(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
            project_root=PROJECT_ROOT,
        ).splitlines()
        if line.strip()
    )
    if changed != (relative,):
        raise RuntimeError(
            "Mechanism-audit config freeze commit must change exactly "
            f"{relative}. Observed: {changed}"
        )
    if config["parent_evidence_commit"] != PARENT_EVIDENCE_COMMIT:
        raise ValueError("Mechanism audit references the wrong parent evidence commit.")
    if (
        config["parent_compact_export_manifest_sha256"]
        != PARENT_COMPACT_EXPORT_MANIFEST_SHA256
    ):
        raise ValueError("Mechanism audit references wrong compact evidence.")
    if (
        config["parent_confirmatory_aggregate_sha256"]
        != PARENT_CONFIRMATORY_AGGREGATE_SHA256
    ):
        raise ValueError("Mechanism audit references wrong confirmatory evidence.")
    if config["protocol_path"] != PROTOCOL_PATH:
        raise ValueError("Mechanism audit references wrong protocol path.")
    if tuple(config["seeds"]) != SEEDS:
        raise ValueError("Mechanism audit seed set changed.")
    if tuple(config["target_arms"]) != TARGET_ARMS:
        raise ValueError("Mechanism audit target-arm set changed.")
    if tuple(config["mechanisms"]) != MECHANISMS:
        raise ValueError("Mechanism audit mechanism set changed.")
    if tuple(config["domains"]) != DOMAINS:
        raise ValueError("Mechanism audit domain set changed.")
    if int(config["boundary_index"]) != BOUNDARY_INDEX:
        raise ValueError("Mechanism audit boundary changed.")
    if int(config["stream_rows"]) != STREAM_ROWS:
        raise ValueError("Mechanism audit stream length changed.")
    if config["row_level_mechanism_trace_accessed_during_preparation"] is not False:
        raise ValueError("Mechanism config claims row-level access during preparation.")
    expected_files = {
        "protocol_sha256": PROJECT_ROOT / PROTOCOL_PATH,
        "source_sha256": (
            PROJECT_ROOT / "src" / "concept_drift_ids" / "cd_primary_mechanism.py"
        ),
        "runner_sha256": PROJECT_ROOT / "run.py",
        "tests_sha256": PROJECT_ROOT / "tests" / "test_cd_primary_mechanism_unit.py",
    }
    for key, path in expected_files.items():
        if sha256_file(path) != str(config[key]):
            raise ValueError(f"Mechanism audit source identity changed: {path}")
    return config


def _trace_summary(seed: int, arm: str) -> dict[str, Any]:
    path = (
        COMPACT_ROOT
        / "phase_c_offline_evaluation_v1_1"
        / f"seed-{seed}"
        / f"{arm}_evaluation.json"
    )
    summary = _read_verified_json(path)
    stored = summary.pop("summary_sha256", None)
    if stored != canonical_sha256(summary):
        raise ValueError(f"Arm summary canonical hash mismatch: seed={seed}, arm={arm}")
    return summary


def _phase_b_arm_manifest(seed: int, arm: str) -> dict[str, Any]:
    path = (
        COMPACT_ROOT
        / "phase_b_symbolic_arms"
        / f"seed-{seed}"
        / arm
        / "arm_manifest.json"
    )
    manifest = _read_verified_json(path)
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError(f"Phase-B arm manifest hash mismatch: seed={seed}, arm={arm}")
    return manifest


def _trace_path(seed: int, arm: str, summary: Mapping[str, Any]) -> Path:
    return (
        HEAVY_PHASE_C_ROOT
        / f"seed-{seed}"
        / str(summary["prediction_trace"]["path"])
    )


def _verify_compressed_trace(path: Path, descriptor: Mapping[str, Any]) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required frozen heavy trace is missing: {path}. "
            "Do not regenerate Stage-8 evidence; restore the original artifact."
        )
    actual = sha256_file(path)
    if actual != str(descriptor["sha256"]):
        raise ValueError(
            f"Compressed prediction-trace SHA mismatch: {path}; "
            f"expected {descriptor['sha256']}, got {actual}"
        )


def _iter_trace(
    path: Path,
    *,
    expected_canonical_jsonl_sha256: str,
    expected_rows: int,
) -> Iterable[dict[str, Any]]:
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "rb") as stream:
        for raw in stream:
            if not raw.strip():
                continue
            digest.update(raw)
            count += 1
            yield json.loads(raw)
    if count != int(expected_rows):
        raise ValueError(
            f"Trace row-count mismatch for {path}: expected {expected_rows}, got {count}"
        )
    if digest.hexdigest() != str(expected_canonical_jsonl_sha256):
        raise ValueError(f"Canonical JSONL trace SHA mismatch: {path}")


def _confusion(y: np.ndarray, p: np.ndarray) -> dict[str, int]:
    return {
        "tp": int(np.sum((y == 1) & (p == 1))),
        "tn": int(np.sum((y == 0) & (p == 0))),
        "fp": int(np.sum((y == 0) & (p == 1))),
        "fn": int(np.sum((y == 1) & (p == 0))),
    }


def _authority_state(c_covered: bool, t_covered: bool) -> str:
    if c_covered and not t_covered:
        return "withdrawal"
    if not c_covered and t_covered:
        return "addition"
    if c_covered and t_covered:
        return "retained_authority"
    return "neither_authoritative"


def _domain_of(index: int) -> str:
    return "pre" if index < BOUNDARY_INDEX else "post"


def _new_version_counter() -> dict[str, Any]:
    return {
        "first_origin_index": None,
        "last_origin_index": None,
        "row_count": 0,
        "covered_count": 0,
        "c_error_count": 0,
        "target_error_count": 0,
        "rescue_count": 0,
        "harm_count": 0,
        "authority_counts": {name: 0 for name in (*MECHANISMS, "neither_authoritative")},
    }


def _collect_comparison(seed: int, target_arm: str) -> tuple[dict[str, Any], dict[str, Any]]:
    c_summary = _trace_summary(seed, "c_frozen_symbolic")
    t_summary = _trace_summary(seed, target_arm)
    c_descriptor = c_summary["prediction_trace"]
    t_descriptor = t_summary["prediction_trace"]
    c_path = _trace_path(seed, "c_frozen_symbolic", c_summary)
    t_path = _trace_path(seed, target_arm, t_summary)
    _verify_compressed_trace(c_path, c_descriptor)
    _verify_compressed_trace(t_path, t_descriptor)

    c_iter = _iter_trace(
        c_path,
        expected_canonical_jsonl_sha256=str(c_descriptor["canonical_jsonl_sha256"]),
        expected_rows=int(c_descriptor["row_count"]),
    )
    t_iter = _iter_trace(
        t_path,
        expected_canonical_jsonl_sha256=str(t_descriptor["canonical_jsonl_sha256"]),
        expected_rows=int(t_descriptor["row_count"]),
    )

    domains: dict[str, dict[str, list[Any]]] = {
        domain: {
            "y": [],
            "c": [],
            "t": [],
            "state": [],
            "c_uncovered": [],
            "c_conflict": [],
            "t_uncovered": [],
            "t_conflict": [],
            "version": [],
        }
        for domain in DOMAINS
    }
    version_counts: dict[str, dict[str, dict[str, Any]]] = {
        domain: defaultdict(_new_version_counter)
        for domain in DOMAINS
    }

    row_count = 0
    sentinel = object()
    for c_row, t_row in itertools.zip_longest(c_iter, t_iter, fillvalue=sentinel):
        if c_row is sentinel or t_row is sentinel:
            raise ValueError("C/target trace length mismatch.")
        row_count += 1

        invariant_fields = (
            "row_id",
            "origin_index",
            "true_label",
            "neural_checkpoint_sha256",
            "neural_probability",
            LAMBDA_ONE_SCORE_KEY,
            LAMBDA_ONE_DECISION_KEY,
        )
        for field in invariant_fields:
            if c_row[field] != t_row[field]:
                raise ValueError(
                    f"Shared-trajectory invariant failed for seed={seed}, "
                    f"target={target_arm}, row={c_row.get('origin_index')}, field={field}"
                )

        index = int(c_row["origin_index"])
        if index != row_count - 1:
            raise ValueError("Trace origin indices are not contiguous.")
        y = int(c_row["true_label"])
        c_decision = int(c_row[PRIMARY_DECISION_KEY])
        t_decision = int(t_row[PRIMARY_DECISION_KEY])
        c_covered = bool(c_row["covered"])
        t_covered = bool(t_row["covered"])
        state = _authority_state(c_covered, t_covered)

        if state == "neither_authoritative" and c_decision != t_decision:
            raise ValueError(
                "Primary decisions differ while neither arm has symbolic authority."
            )

        domain = _domain_of(index)
        bucket = domains[domain]
        bucket["y"].append(y)
        bucket["c"].append(c_decision)
        bucket["t"].append(t_decision)
        bucket["state"].append(state)
        bucket["c_uncovered"].append(bool(c_row["uncovered"]))
        bucket["c_conflict"].append(bool(c_row["conflict_abstain"]))
        bucket["t_uncovered"].append(bool(t_row["uncovered"]))
        bucket["t_conflict"].append(bool(t_row["conflict_abstain"]))
        version = str(t_row["rule_base_version_id"])
        bucket["version"].append(version)

        counter = version_counts[domain][version]
        counter["first_origin_index"] = (
            index if counter["first_origin_index"] is None
            else min(int(counter["first_origin_index"]), index)
        )
        counter["last_origin_index"] = (
            index if counter["last_origin_index"] is None
            else max(int(counter["last_origin_index"]), index)
        )
        counter["row_count"] += 1
        counter["covered_count"] += int(t_covered)
        c_correct = c_decision == y
        t_correct = t_decision == y
        counter["c_error_count"] += int(not c_correct)
        counter["target_error_count"] += int(not t_correct)
        counter["rescue_count"] += int((not c_correct) and t_correct)
        counter["harm_count"] += int(c_correct and (not t_correct))
        counter["authority_counts"][state] += 1

    if row_count != STREAM_ROWS:
        raise ValueError(
            f"Unexpected trace rows for seed={seed}, target={target_arm}: {row_count}"
        )

    phase_b = _phase_b_arm_manifest(seed, target_arm)
    publication_index = {
        str(item["rule_base_version_id"]): int(item["effective_index"])
        for item in phase_b["publications"]
    }
    publication_index[str(phase_b["initial_rule_base_version_id"])] = 0

    version_payload: dict[str, Any] = {}
    for domain in DOMAINS:
        version_payload[domain] = {}
        for version, counter in sorted(version_counts[domain].items()):
            effective = publication_index.get(version)
            if effective is None:
                raise ValueError(
                    f"Trace references unknown target rule-base version: {version}"
                )
            timing = (
                "initial"
                if effective == 0
                else "pre_reference"
                if effective < BOUNDARY_INDEX
                else "post_reference"
            )
            rows = int(counter["row_count"])
            version_payload[domain][version] = {
                **counter,
                "publication_effective_index": effective,
                "publication_timing": timing,
                "covered_rate": counter["covered_count"] / rows,
                "net_corrected_decisions": (
                    counter["rescue_count"] - counter["harm_count"]
                ),
            }

    trace_inputs = {
        "c_frozen_symbolic": {
            "path": c_path.relative_to(PROJECT_ROOT).as_posix(),
            **dict(c_descriptor),
        },
        target_arm: {
            "path": t_path.relative_to(PROJECT_ROOT).as_posix(),
            **dict(t_descriptor),
        },
    }
    return {
        "domains": domains,
        "version_context": version_payload,
        "trace_inputs": trace_inputs,
        "stored_mcc": {
            domain: {
                "c": float(
                    c_summary["metrics_by_neural_weight"]["0.5"][domain]["mcc"]
                ),
                "target": float(
                    t_summary["metrics_by_neural_weight"]["0.5"][domain]["mcc"]
                ),
            }
            for domain in DOMAINS
        },
    }, phase_b


def _stratum_summary(
    *,
    y: np.ndarray,
    c: np.ndarray,
    t: np.ndarray,
    state: np.ndarray,
    c_uncovered: np.ndarray,
    c_conflict: np.ndarray,
    t_uncovered: np.ndarray,
    t_conflict: np.ndarray,
    name: str,
) -> dict[str, Any]:
    mask = state == name
    rows = int(mask.sum())
    if rows == 0:
        return {
            "row_count": 0,
            "row_fraction": 0.0,
            "benign_rows": 0,
            "attack_rows": 0,
            "c_error_count": 0,
            "target_error_count": 0,
            "rescue_count": 0,
            "harm_count": 0,
            "net_corrected_decisions": 0,
            "c_confusion": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
            "target_confusion": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
            "c_uncovered_count": 0,
            "c_conflict_count": 0,
            "target_uncovered_count": 0,
            "target_conflict_count": 0,
        }
    y_s = y[mask]
    c_s = c[mask]
    t_s = t[mask]
    c_correct = c_s == y_s
    t_correct = t_s == y_s
    rescues = int(np.sum((~c_correct) & t_correct))
    harms = int(np.sum(c_correct & (~t_correct)))
    return {
        "row_count": rows,
        "row_fraction": rows / len(y),
        "benign_rows": int(np.sum(y_s == 0)),
        "attack_rows": int(np.sum(y_s == 1)),
        "c_error_count": int(np.sum(~c_correct)),
        "target_error_count": int(np.sum(~t_correct)),
        "rescue_count": rescues,
        "harm_count": harms,
        "net_corrected_decisions": rescues - harms,
        "c_confusion": _confusion(y_s, c_s),
        "target_confusion": _confusion(y_s, t_s),
        "c_uncovered_count": int(np.sum(c_uncovered[mask])),
        "c_conflict_count": int(np.sum(c_conflict[mask])),
        "target_uncovered_count": int(np.sum(t_uncovered[mask])),
        "target_conflict_count": int(np.sum(t_conflict[mask])),
    }


def _hybrid_mcc(
    y: np.ndarray,
    c: np.ndarray,
    t: np.ndarray,
    state: np.ndarray,
    enabled: frozenset[str],
) -> float:
    hybrid = c.copy()
    for mechanism in enabled:
        mask = state == mechanism
        hybrid[mask] = t[mask]
    return float(matthews_corrcoef(y, hybrid))


def _shapley_mcc(
    *,
    y: np.ndarray,
    c: np.ndarray,
    t: np.ndarray,
    state: np.ndarray,
) -> dict[str, Any]:
    mechanisms = tuple(MECHANISMS)
    values: dict[frozenset[str], float] = {}
    for size in range(len(mechanisms) + 1):
        for subset in itertools.combinations(mechanisms, size):
            key = frozenset(subset)
            values[key] = _hybrid_mcc(y, c, t, state, key)

    shapley: dict[str, float] = {name: 0.0 for name in mechanisms}
    n = len(mechanisms)
    for mechanism in mechanisms:
        others = tuple(name for name in mechanisms if name != mechanism)
        for size in range(len(others) + 1):
            for subset in itertools.combinations(others, size):
                s = frozenset(subset)
                weight = (
                    math.factorial(len(s))
                    * math.factorial(n - len(s) - 1)
                    / math.factorial(n)
                )
                shapley[mechanism] += weight * (
                    values[s | {mechanism}] - values[s]
                )

    c_mcc = values[frozenset()]
    target_mcc = values[frozenset(mechanisms)]
    total = target_mcc - c_mcc
    if not math.isclose(
        sum(shapley.values()),
        total,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise AssertionError("MCC Shapley efficiency invariant failed.")
    return {
        "c_mcc": c_mcc,
        "target_mcc": target_mcc,
        "total_mcc_difference": total,
        "shapley_mcc_contribution": shapley,
        "coalition_mcc": {
            "+".join(sorted(key)) if key else "none": value
            for key, value in sorted(
                values.items(),
                key=lambda item: (len(item[0]), tuple(sorted(item[0]))),
            )
        },
    }


def _analyze_domain(
    raw: Mapping[str, list[Any]],
    *,
    stored_mcc: Mapping[str, float],
) -> dict[str, Any]:
    y = np.asarray(raw["y"], dtype=np.int8)
    c = np.asarray(raw["c"], dtype=np.int8)
    t = np.asarray(raw["t"], dtype=np.int8)
    state = np.asarray(raw["state"], dtype=object)
    c_uncovered = np.asarray(raw["c_uncovered"], dtype=bool)
    c_conflict = np.asarray(raw["c_conflict"], dtype=bool)
    t_uncovered = np.asarray(raw["t_uncovered"], dtype=bool)
    t_conflict = np.asarray(raw["t_conflict"], dtype=bool)

    shapley = _shapley_mcc(y=y, c=c, t=t, state=state)
    if not math.isclose(
        shapley["c_mcc"],
        float(stored_mcc["c"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Recomputed C MCC does not match frozen summary.")
    if not math.isclose(
        shapley["target_mcc"],
        float(stored_mcc["target"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Recomputed target MCC does not match frozen summary.")

    strata = {
        name: _stratum_summary(
            y=y,
            c=c,
            t=t,
            state=state,
            c_uncovered=c_uncovered,
            c_conflict=c_conflict,
            t_uncovered=t_uncovered,
            t_conflict=t_conflict,
            name=name,
        )
        for name in (*MECHANISMS, "neither_authoritative")
    }
    return {
        "row_count": int(len(y)),
        "strata": strata,
        "mcc_decomposition": shapley,
        "total_rescue_count": int(
            sum(strata[name]["rescue_count"] for name in MECHANISMS)
        ),
        "total_harm_count": int(
            sum(strata[name]["harm_count"] for name in MECHANISMS)
        ),
        "total_net_corrected_decisions": int(
            sum(strata[name]["net_corrected_decisions"] for name in MECHANISMS)
        ),
    }


def analyze_seed(seed: int) -> dict[str, Any]:
    if seed not in SEEDS:
        raise ValueError(f"Unsupported mechanism-audit seed: {seed}")
    comparisons: dict[str, Any] = {}
    trace_inputs: dict[str, Any] = {}
    for target in TARGET_ARMS:
        collected, phase_b = _collect_comparison(seed, target)
        domains = {
            domain: _analyze_domain(
                collected["domains"][domain],
                stored_mcc=collected["stored_mcc"][domain],
            )
            for domain in DOMAINS
        }
        comparisons[target] = {
            "target_arm": target,
            "domains": domains,
            "rule_version_context": collected["version_context"],
            "phase_b_arm_manifest_sha256": phase_b["manifest_sha256"],
            "initial_rule_base_version_id": phase_b[
                "initial_rule_base_version_id"
            ],
            "final_rule_base_version_id": phase_b[
                "final_rule_base_version_id"
            ],
            "publications": phase_b["publications"],
        }
        trace_inputs[target] = collected["trace_inputs"]
    return {
        "schema_version": 1,
        "seed": seed,
        "status": "symbolic_value_mechanism_audit_complete",
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "parent_compact_export_manifest_sha256": (
            PARENT_COMPACT_EXPORT_MANIFEST_SHA256
        ),
        "comparisons": comparisons,
        "trace_inputs": trace_inputs,
    }


def _numeric_summary(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "values": [float(value) for value in array],
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "sample_sd": float(array.std(ddof=1)),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
        "positive": int(np.sum(array > 0)),
        "zero": int(np.sum(array == 0)),
        "negative": int(np.sum(array < 0)),
    }


def build_aggregate(seed_results: Mapping[int, Mapping[str, Any]]) -> dict[str, Any]:
    if tuple(sorted(seed_results)) != SEEDS:
        raise ValueError("Mechanism aggregate requires exactly seeds 0..4.")
    aggregate: dict[str, Any] = {}
    for target in TARGET_ARMS:
        target_payload: dict[str, Any] = {}
        for domain in DOMAINS:
            domain_payload: dict[str, Any] = {
                "total_mcc_difference": _numeric_summary(
                    [
                        float(
                            seed_results[seed]["comparisons"][target]["domains"][
                                domain
                            ]["mcc_decomposition"]["total_mcc_difference"]
                        )
                        for seed in SEEDS
                    ]
                ),
                "mechanisms": {},
            }
            for mechanism in MECHANISMS:
                domain_payload["mechanisms"][mechanism] = {
                    "shapley_mcc_contribution": _numeric_summary(
                        [
                            float(
                                seed_results[seed]["comparisons"][target][
                                    "domains"
                                ][domain]["mcc_decomposition"][
                                    "shapley_mcc_contribution"
                                ][mechanism]
                            )
                            for seed in SEEDS
                        ]
                    ),
                    "net_corrected_decisions": _numeric_summary(
                        [
                            float(
                                seed_results[seed]["comparisons"][target][
                                    "domains"
                                ][domain]["strata"][mechanism][
                                    "net_corrected_decisions"
                                ]
                            )
                            for seed in SEEDS
                        ]
                    ),
                    "row_fraction": _numeric_summary(
                        [
                            float(
                                seed_results[seed]["comparisons"][target][
                                    "domains"
                                ][domain]["strata"][mechanism]["row_fraction"]
                            )
                            for seed in SEEDS
                        ]
                    ),
                }
            target_payload[domain] = domain_payload
        aggregate[target] = target_payload

    return {
        "schema_version": 1,
        "status": "symbolic_value_mechanism_aggregate_complete",
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "parent_compact_export_manifest_sha256": (
            PARENT_COMPACT_EXPORT_MANIFEST_SHA256
        ),
        "seed_count": len(SEEDS),
        "targets": aggregate,
        "inference": (
            "exploratory_descriptive_post_primary_no_new_pvalue_family"
        ),
    }


def execute_mechanism_audit() -> dict[str, Any]:
    config = verify_mechanism_config_for_execution()
    _verify_parent_compact_evidence()
    if OUTPUT_ROOT.exists():
        raise FileExistsError(
            f"Refusing to reuse mechanism-audit output root: {OUTPUT_ROOT}"
        )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)

    seed_results: dict[int, dict[str, Any]] = {}
    files: dict[str, dict[str, Any]] = {}
    try:
        for seed in SEEDS:
            result = analyze_seed(seed)
            result["mechanism_config_manifest_sha256"] = config[
                "manifest_sha256"
            ]
            result["result_sha256"] = canonical_sha256(result)
            path = OUTPUT_ROOT / f"seed-{seed}.json"
            file_sha = write_json_new(path, result)
            files[f"seed_{seed}"] = {
                "path": path.name,
                "sha256": file_sha,
                "canonical_sha256": result["result_sha256"],
            }
            seed_results[seed] = result

        aggregate = build_aggregate(seed_results)
        aggregate["mechanism_config_manifest_sha256"] = config[
            "manifest_sha256"
        ]
        aggregate["aggregate_sha256"] = canonical_sha256(aggregate)
        aggregate_path = OUTPUT_ROOT / "aggregate.json"
        aggregate_file_sha = write_json_new(aggregate_path, aggregate)
        files["aggregate"] = {
            "path": aggregate_path.name,
            "sha256": aggregate_file_sha,
            "canonical_sha256": aggregate["aggregate_sha256"],
        }

        manifest = {
            "schema_version": 1,
            "status": "symbolic_value_mechanism_audit_written",
            "mechanism_config_manifest_sha256": config["manifest_sha256"],
            "source_commit": config["source_commit"],
            "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
            "parent_compact_export_manifest_sha256": (
                PARENT_COMPACT_EXPORT_MANIFEST_SHA256
            ),
            "parent_confirmatory_aggregate_sha256": (
                PARENT_CONFIRMATORY_AGGREGATE_SHA256
            ),
            "protocol_path": PROTOCOL_PATH,
            "files": files,
        }
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        write_json_new(OUTPUT_ROOT / "audit_manifest.json", manifest)
        verified = verify_mechanism_audit()
        return {
            "status": "symbolic_value_mechanism_audit_written",
            "seed_count": len(SEEDS),
            "manifest_sha256": verified["manifest_sha256"],
            "aggregate_sha256": verified["aggregate_sha256"],
        }
    except Exception:
        # Preserve any partial write-once evidence. Do not silently clean it.
        raise


def verify_mechanism_audit() -> dict[str, Any]:
    config = verify_mechanism_config_for_execution(require_fully_clean=False)
    _verify_parent_compact_evidence()
    manifest_path = OUTPUT_ROOT / "audit_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Mechanism-audit manifest is absent.")
    manifest = _read_verified_json(manifest_path)
    stored_manifest = manifest.pop("manifest_sha256", None)
    if stored_manifest != canonical_sha256(manifest):
        raise ValueError("Mechanism-audit manifest canonical hash mismatch.")
    if manifest["mechanism_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Mechanism audit references wrong frozen config.")
    if manifest["parent_evidence_commit"] != PARENT_EVIDENCE_COMMIT:
        raise ValueError("Mechanism audit references wrong parent evidence.")

    seed_results: dict[int, dict[str, Any]] = {}
    for seed in SEEDS:
        descriptor = manifest["files"][f"seed_{seed}"]
        path = OUTPUT_ROOT / str(descriptor["path"])
        if sha256_file(path) != descriptor["sha256"]:
            raise ValueError(f"Mechanism seed file hash mismatch: seed={seed}")
        payload = _read_verified_json(path)
        stored = payload.pop("result_sha256", None)
        if stored != canonical_sha256(payload):
            raise ValueError(f"Mechanism seed canonical hash mismatch: seed={seed}")
        if stored != descriptor["canonical_sha256"]:
            raise ValueError(f"Mechanism seed manifest binding mismatch: seed={seed}")
        seed_results[seed] = {**payload, "result_sha256": stored}

    aggregate_descriptor = manifest["files"]["aggregate"]
    aggregate_path = OUTPUT_ROOT / str(aggregate_descriptor["path"])
    if sha256_file(aggregate_path) != aggregate_descriptor["sha256"]:
        raise ValueError("Mechanism aggregate file hash mismatch.")
    aggregate = _read_verified_json(aggregate_path)
    stored_aggregate = aggregate.pop("aggregate_sha256", None)
    if stored_aggregate != canonical_sha256(aggregate):
        raise ValueError("Mechanism aggregate canonical hash mismatch.")
    if stored_aggregate != aggregate_descriptor["canonical_sha256"]:
        raise ValueError("Mechanism aggregate manifest binding mismatch.")

    regenerated = build_aggregate(seed_results)
    regenerated["mechanism_config_manifest_sha256"] = config["manifest_sha256"]
    if canonical_sha256(regenerated) != stored_aggregate:
        raise ValueError("Mechanism aggregate does not regenerate from seed evidence.")

    return {
        "status": "symbolic_value_mechanism_audit_verified",
        "seed_count": len(SEEDS),
        "manifest_sha256": stored_manifest,
        "aggregate_sha256": stored_aggregate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post-primary symbolic-value mechanism audit."
    )
    parser.add_argument("--prepare-config", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_config and args.verify_only:
        parser.error("--prepare-config and --verify-only are mutually exclusive.")
    if args.prepare_config:
        payload = write_mechanism_config()
        result = {
            "status": "symbolic_value_mechanism_config_written",
            "path": CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "manifest_sha256": payload["manifest_sha256"],
            "source_commit": payload["source_commit"],
            "row_level_mechanism_trace_accessed_during_preparation": False,
            "next_gate": (
                "commit only the mechanism-audit config and require exact-head CI"
            ),
        }
    else:
        result = (
            verify_mechanism_audit()
            if args.verify_only
            else execute_mechanism_audit()
        )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
