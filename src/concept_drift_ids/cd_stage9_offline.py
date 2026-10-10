from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_primary_adapter import EXPECTED_PRE_ROWS
from concept_drift_ids.cd_primary_phase_b import ARM_NAMES
from concept_drift_ids.cd_primary_phase_c import (
    _recovery_summary,
    _safe_binary_metrics,
    _safe_explanation,
)
from concept_drift_ids.cd_implementation_preflight import PROJECT_ROOT
from concept_drift_ids.cd_stage9_config import (
    OFFLINE_CONDITIONS,
    PRIMARY_SEEDS,
    STAGE8_COMPACT_ROOT,
    STAGE9_OUTPUT_ROOT,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import reporting_windows


PRIMARY_HEAVY_PHASE_C = (
    PROJECT_ROOT
    / "artifacts"
    / "cd_primary_v1"
    / "phase_c_offline_evaluation_v1_1"
)


def _compact_eval_path(seed: int, arm: str) -> Path:
    return (
        STAGE8_COMPACT_ROOT
        / "phase_c_offline_evaluation_v1_1"
        / f"seed-{seed}"
        / f"{arm}_evaluation.json"
    )


def _heavy_trace_path(seed: int, arm: str) -> Path:
    return (
        PRIMARY_HEAVY_PHASE_C
        / f"seed-{seed}"
        / f"{arm}_prediction_trace.jsonl.gz"
    )


def _output_dir(condition: str, seed: int) -> Path:
    return STAGE9_OUTPUT_ROOT / "offline" / condition / f"seed-{seed}"


def _read_verified_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload_sha = payload.pop("payload_sha256", None)
    if payload_sha is not None and payload_sha != canonical_sha256(payload):
        raise ValueError(f"JSON payload hash mismatch: {path}")
    return payload


def _verified_trace(seed: int, arm: str) -> list[dict[str, Any]]:
    summary = _read_verified_json(_compact_eval_path(seed, arm))
    trace = summary["prediction_trace"]
    path = _heavy_trace_path(seed, arm)
    if not path.is_file():
        raise FileNotFoundError(
            "Stage-9 offline robustness requires the original frozen Stage-8 "
            f"heavy trace on the execution workspace: {path}"
        )
    if sha256_file(path) != trace["sha256"]:
        raise ValueError("Frozen Stage-8 heavy trace raw hash mismatch.")

    canonical = hashlib.sha256()
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            encoded = line.encode("utf-8")
            canonical.update(encoded)
            rows.append(json.loads(line))
    if canonical.hexdigest() != trace["canonical_jsonl_sha256"]:
        raise ValueError("Frozen Stage-8 trace canonical content hash mismatch.")
    if len(rows) != int(trace["row_count"]) or len(rows) != 138530:
        raise ValueError("Frozen Stage-8 trace row count mismatch.")
    for index, row in enumerate(rows):
        if int(row["origin_index"]) != index:
            raise ValueError("Frozen Stage-8 trace origin order changed.")
    return rows


def _window_result(
    rows: list[dict[str, Any]],
    *,
    window_size: int,
) -> dict[str, Any]:
    y = np.asarray([int(row["true_label"]) for row in rows], dtype=np.int8)
    probability = np.asarray(
        [float(row["fused_probability_lambda_0_5"]) for row in rows],
        dtype=np.float64,
    )
    decision = np.asarray(
        [int(row["decision_lambda_0_5"]) for row in rows], dtype=np.int8
    )
    symbolic_class = np.asarray(
        [int(row["symbolic_class"]) for row in rows], dtype=np.int8
    )
    covered = np.asarray([bool(row["covered"]) for row in rows], dtype=bool)
    uncovered = np.asarray([bool(row["uncovered"]) for row in rows], dtype=bool)
    conflict = np.asarray(
        [bool(row["conflict_abstain"]) for row in rows], dtype=bool
    )

    # Threshold is irrelevant to confusion verification here because stored
    # decisions are authoritative. Use a neutral threshold only for probability
    # metrics; overwrite/verify confusion against the stored decisions.
    out: dict[str, list[dict[str, Any]]] = {"pre": [], "post": []}
    for domain, start, stop in (
        ("pre", 0, EXPECTED_PRE_ROWS),
        ("post", EXPECTED_PRE_ROWS, len(rows)),
    ):
        for local_start, local_stop in reporting_windows(
            stop - start,
            window_size=window_size,
            min_remainder=min(1000, window_size),
        ):
            a = start + local_start
            b = start + local_stop
            s = slice(a, b)
            metrics = _safe_binary_metrics(y[s], probability[s], 0.5)
            stored = decision[s]
            metrics["tp"] = int(np.sum((y[s] == 1) & (stored == 1)))
            metrics["tn"] = int(np.sum((y[s] == 0) & (stored == 0)))
            metrics["fp"] = int(np.sum((y[s] == 0) & (stored == 1)))
            metrics["fn"] = int(np.sum((y[s] == 1) & (stored == 0)))
            if metrics["tp"] + metrics["tn"] + metrics["fp"] + metrics["fn"] != b - a:
                raise AssertionError("Stage-9 window confusion accounting failed.")
            # Recompute decision-derived metrics to avoid an arbitrary threshold.
            from sklearn.metrics import f1_score, matthews_corrcoef
            metrics["mcc"] = float(matthews_corrcoef(y[s], stored))
            metrics["f1"] = float(f1_score(y[s], stored, zero_division=0))
            benign = metrics["tn"] + metrics["fp"]
            metrics["fpr"] = (
                float(metrics["fp"] / benign) if benign else None
            )
            explanation = _safe_explanation(
                y[s],
                symbolic_class=symbolic_class[s],
                covered=covered[s],
                uncovered=uncovered[s],
                conflict=conflict[s],
            )
            out[domain].append(
                {
                    "start_index": a,
                    "end_index_exclusive": b,
                    "row_count": b - a,
                    "mcc": metrics["mcc"],
                    "fpr": metrics["fpr"],
                    "f1": metrics["f1"],
                    "mcsc": explanation["mcsc"],
                    "resolved_coverage": explanation["resolved_coverage"],
                    "conflict_abstain_rate": explanation["conflict_abstain_rate"],
                }
            )
    return {
        "window_size": window_size,
        "windows": out,
        "recovery": _recovery_summary(out),
    }


def execute_offline_condition(condition: str, seed: int) -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    if condition not in OFFLINE_CONDITIONS:
        raise ValueError(f"Unknown Stage-9 offline condition: {condition}")
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")
    out = _output_dir(condition, seed)
    if out.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 offline output: {out}")
    out.mkdir(parents=True, exist_ok=False)

    results: dict[str, Any] = {}
    for arm in ARM_NAMES:
        compact = _read_verified_json(_compact_eval_path(seed, arm))
        if condition.startswith("lambda_"):
            weight = {
                "lambda_0_7": "0.7",
                "lambda_0_9": "0.9",
                "lambda_1_0": "1.0",
            }[condition]
            results[arm] = {
                "source_summary_sha256": compact["summary_sha256"],
                "neural_weight": float(weight),
                "metrics": compact["metrics_by_neural_weight"][weight],
                "recomputed": False,
            }
        else:
            rows = _verified_trace(seed, arm)
            size = 2500 if condition == "window_2500" else 10000
            results[arm] = {
                "source_summary_sha256": compact["summary_sha256"],
                "source_prediction_trace": compact["prediction_trace"],
                "recomputed": True,
                **_window_result(rows, window_size=size),
            }

    payload = {
        "schema_version": 1,
        "status": "stage9_offline_condition_complete",
        "condition_id": condition,
        "seed": seed,
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "stage8_parent": config["stage8_parent"],
        "results": results,
        "adaptive_state_rerun": False,
        "threshold_refit": False,
    }
    payload["result_sha256"] = canonical_sha256(payload)
    write_json_new(out / "result.json", payload)
    return {
        "status": payload["status"],
        "condition_id": condition,
        "seed": seed,
        "result_sha256": payload["result_sha256"],
    }


def verify_offline_condition(condition: str, seed: int) -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    path = _output_dir(condition, seed) / "result.json"
    payload = _read_verified_json(path)
    stored = payload.pop("result_sha256", None)
    if stored != canonical_sha256(payload):
        raise ValueError("Stage-9 offline result canonical hash mismatch.")
    if payload["condition_id"] != condition or int(payload["seed"]) != seed:
        raise ValueError("Stage-9 offline result identity mismatch.")
    if payload["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 offline result references wrong config.")
    if payload["adaptive_state_rerun"] is not False or payload["threshold_refit"] is not False:
        raise ValueError("Stage-9 offline condition changed adaptive state/threshold.")
    return {
        "status": "stage9_offline_condition_verified",
        "condition_id": condition,
        "seed": seed,
        "result_sha256": stored,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", required=True, choices=OFFLINE_CONDITIONS)
    parser.add_argument("--seed", type=int, required=True, choices=PRIMARY_SEEDS)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (
        verify_offline_condition(args.condition, args.seed)
        if args.verify_only
        else execute_offline_condition(args.condition, args.seed)
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
