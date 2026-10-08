from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from threadpoolctl import threadpool_info

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import binary_metrics, predict_probabilities
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import (
    Rule,
    bootstrap_gate_stability,
    canonical_json_hash,
    fuse_scores,
    infer_symbolic,
    reporting_windows,
    rule_quality,
    stratified_bootstrap_indices,
)
from concept_drift_ids.system_a import (
    SYSTEM_A_CONFIG,
    _load_checkpoint_model,
    _load_frozen_system_a_manifest,
)
from concept_drift_ids.system_b import (
    RULE_STALENESS_METRICS,
    SYSTEM_B_CONFIG,
    _build_metric_tables,
    _confusion,
    _git_state,
    _rule_from_dict,
    _rule_staleness_deltas,
    _runtime,
    _safe_window_metrics,
    _write_csv_new,
    _write_json_new,
)
from concept_drift_ids.system_b_r0_v2 import (
    ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256,
    SYSTEM_B_V2_ID,
    load_accepted_r0_v2_manifest,
)


EVALUATION_ID = "system_b_v2_corrected_evaluation_v1"
EVALUATION_DIR = PROJECT_ROOT / "results" / "frozen" / "system_b_v2_corrected_v1"
EVALUATION_MANIFEST_PATH = EVALUATION_DIR / "evaluation_manifest.json"

V2_EVIDENCE_METRICS = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "f1",
    "fpr",
    "mcc",
    "roc_auc",
    "average_precision",
    "resolved_coverage",
    "raw_activation_coverage",
    "uncovered_rate",
    "conflict_abstention_rate",
    "symbolic_neural_fidelity",
    "benign_resolved_coverage",
    "attack_resolved_coverage",
    "benign_symbolic_correctness",
    "attack_symbolic_correctness",
    "benign_symbolic_neural_fidelity",
    "attack_symbolic_neural_fidelity",
)

TIMING_WARMUP_REPEATS = 1
TIMING_MEASURED_REPEATS = 5
_ALLOWED_PARTITIONS = {"pre_drift", "post_drift"}


def _load_evaluation_partition(name: str):
    if name not in _ALLOWED_PARTITIONS:
        raise ValueError(f"R0.v2 evaluator forbids partition {name!r}.")
    return load_partition(name)


def _load_v2_rules(manifest: dict[str, Any], seed: int) -> list[Rule]:
    entry = manifest["rule_artifacts"][str(seed)]
    payload = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
    return [_rule_from_dict(item) for item in payload["rules"]]


def _class_conditional_symbolic_summary(
    symbolic: dict[str, np.ndarray],
    neural_decision: np.ndarray,
    y_true: np.ndarray,
) -> dict[str, float | None]:
    y = np.asarray(y_true, dtype=np.int8)
    neural = np.asarray(neural_decision, dtype=np.int8)
    covered = np.asarray(symbolic["covered"], dtype=bool)
    symbolic_class = np.asarray(symbolic["symbolic_class"], dtype=np.int8)
    out: dict[str, float | None] = {}
    for class_value, prefix in ((0, "benign"), (1, "attack")):
        class_mask = y == class_value
        if not np.any(class_mask):
            out[f"{prefix}_resolved_coverage"] = None
            out[f"{prefix}_symbolic_correctness"] = None
            out[f"{prefix}_symbolic_neural_fidelity"] = None
            continue
        resolved = class_mask & covered
        out[f"{prefix}_resolved_coverage"] = float(
            np.sum(resolved) / np.sum(class_mask)
        )
        if not np.any(resolved):
            out[f"{prefix}_symbolic_correctness"] = None
            out[f"{prefix}_symbolic_neural_fidelity"] = None
        else:
            out[f"{prefix}_symbolic_correctness"] = float(
                np.mean(symbolic_class[resolved] == class_value)
            )
            out[f"{prefix}_symbolic_neural_fidelity"] = float(
                np.mean(symbolic_class[resolved] == neural[resolved])
            )
    return out


def _symbolic_summary(
    symbolic: dict[str, np.ndarray],
    neural_decision: np.ndarray,
    y_true: np.ndarray,
) -> dict[str, float | None]:
    covered = symbolic["covered"]
    symbolic_class = symbolic["symbolic_class"]
    base = {
        "resolved_coverage": float(np.mean(covered)),
        "raw_activation_coverage": float(np.mean(symbolic["raw_activated"])),
        "uncovered_rate": float(np.mean(symbolic["uncovered"])),
        "conflict_abstention_rate": float(np.mean(symbolic["conflict_abstain"])),
        "symbolic_neural_fidelity": (
            float(np.mean(symbolic_class[covered] == neural_decision[covered]))
            if np.any(covered)
            else None
        ),
    }
    base.update(
        _class_conditional_symbolic_summary(symbolic, neural_decision, y_true)
    )
    return base


def _imputation_diagnostic(
    raw_frame,
    *,
    mask: np.ndarray,
    rule: Rule,
    y_true: np.ndarray,
    neural_decision: np.ndarray,
) -> dict[str, float | int | None]:
    features = sorted({condition.feature for condition in rule.conditions})
    missing_any = raw_frame.loc[:, features].isna().any(axis=1).to_numpy(dtype=bool)
    activated = np.asarray(mask, dtype=bool)
    imputed_activated = activated & missing_any
    count = int(np.sum(imputed_activated))
    activation_count = int(np.sum(activated))
    clean_mask = activated & ~missing_any
    clean_quality = rule_quality(
        clean_mask,
        y_true=y_true,
        neural_decision=neural_decision,
        consequent=rule.consequent,
    )
    return {
        "imputed_antecedent_activation_count": count,
        "imputed_antecedent_activation_fraction": (
            float(count / activation_count) if activation_count else None
        ),
        "imputation_free_support": float(clean_quality["support"]),
        "imputation_free_covered_count": int(clean_quality["covered_count"]),
        "imputation_free_class_precision": float(clean_quality["class_precision"]),
        "imputation_free_neural_fidelity": float(clean_quality["neural_fidelity"]),
    }


def _thread_runtime() -> dict[str, object]:
    state = _runtime()
    state["torch_num_threads"] = int(torch.get_num_threads())
    state["torch_num_interop_threads"] = int(torch.get_num_interop_threads())
    state["thread_environment"] = {
        key: os.environ.get(key)
        for key in (
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        )
    }
    state["threadpools"] = threadpool_info()
    return state


def _timed_symbolic_fusion(
    X: np.ndarray,
    neural_prob: np.ndarray,
    *,
    feature_names,
    rules: list[Rule],
    neural_weight: float,
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, float | int]]:
    primary_symbolic = infer_symbolic(X, feature_names=feature_names, rules=rules)
    primary_fused = fuse_scores(
        neural_prob, primary_symbolic, neural_weight=neural_weight
    )

    for _ in range(TIMING_WARMUP_REPEATS):
        warm_symbolic = infer_symbolic(X, feature_names=feature_names, rules=rules)
        warm_fused = fuse_scores(
            neural_prob, warm_symbolic, neural_weight=neural_weight
        )
        if not np.array_equal(warm_symbolic["covered"], primary_symbolic["covered"]):
            raise RuntimeError("Symbolic timing warm-up changed coverage state.")
        if not np.allclose(warm_fused, primary_fused, rtol=0.0, atol=0.0):
            raise RuntimeError("Symbolic timing warm-up changed fused scores.")

    durations: list[float] = []
    for _ in range(TIMING_MEASURED_REPEATS):
        started = time.perf_counter()
        repeat_symbolic = infer_symbolic(X, feature_names=feature_names, rules=rules)
        repeat_fused = fuse_scores(
            neural_prob, repeat_symbolic, neural_weight=neural_weight
        )
        durations.append(time.perf_counter() - started)
        for key in ("covered", "uncovered", "conflict_abstain", "raw_activated", "symbolic_class"):
            if not np.array_equal(repeat_symbolic[key], primary_symbolic[key]):
                raise RuntimeError(f"Timed symbolic repeat changed {key}.")
        if not np.allclose(repeat_fused, primary_fused, rtol=0.0, atol=0.0):
            raise RuntimeError("Timed symbolic repeat changed fused scores.")

    array = np.asarray(durations, dtype=np.float64)
    return primary_symbolic, primary_fused, {
        "symbolic_fusion_warmup_repeats": TIMING_WARMUP_REPEATS,
        "symbolic_fusion_measured_repeats": TIMING_MEASURED_REPEATS,
        "symbolic_fusion_seconds_median": float(np.median(array)),
        "symbolic_fusion_seconds_min": float(np.min(array)),
        "symbolic_fusion_seconds_max": float(np.max(array)),
        "symbolic_fusion_seconds_p25": float(np.percentile(array, 25)),
        "symbolic_fusion_seconds_p75": float(np.percentile(array, 75)),
    }


def evaluate_r0_v2(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("Corrected System-B v2 evaluation is frozen to CPU.")
    if EVALUATION_MANIFEST_PATH.exists() or EVALUATION_DIR.exists():
        raise FileExistsError(
            "Corrected System-B v2 evaluation already exists; refusing overwrite."
        )

    evaluation_git = _git_state(require_clean=True)
    manifest = load_accepted_r0_v2_manifest()
    if manifest["manifest_sha256"] != ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256:
        raise ValueError("Evaluator is not using the accepted R0.v2 manifest.")
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    neural_weight = float(manifest["fusion"]["selected_neural_weight"])
    runtime = _thread_runtime()
    device = torch.device("cpu")

    detection_rows: list[dict[str, object]] = []
    rule_rows: list[dict[str, object]] = []
    window_rows: list[dict[str, object]] = []
    runtime_rows: list[dict[str, object]] = []

    for partition_name in ("pre_drift", "post_drift"):
        partition = _load_evaluation_partition(partition_name)
        raw_X = partition.X
        X = transform_frame(raw_X, preprocessing, dtype=np.dtype("float32"))
        y = partition.y.to_numpy(dtype=np.int8, copy=True)

        for seed in SYSTEM_B_CONFIG["seeds"]:
            record = next(
                row for row in frozen_a["seed_records"] if int(row["seed"]) == seed
            )
            model = _load_checkpoint_model(
                record, device=device, preprocessing_hash=preprocessing.state_hash
            )
            neural_started = time.perf_counter()
            neural_prob = predict_probabilities(
                model,
                X,
                device=device,
                batch_size=SYSTEM_A_CONFIG["batch_size"],
            )
            neural_seconds = time.perf_counter() - neural_started
            neural_decision = (
                neural_prob >= float(record["threshold"])
            ).astype(np.int8)
            rules = _load_v2_rules(manifest, seed)
            symbolic, fused, timing = _timed_symbolic_fusion(
                X,
                neural_prob,
                feature_names=preprocessing.feature_columns,
                rules=rules,
                neural_weight=neural_weight,
            )
            threshold = float(
                manifest["fusion"]["per_seed_thresholds"][str(seed)]
            )
            metrics = binary_metrics(y, fused, threshold)
            detection_rows.append({
                "system_id": SYSTEM_B_V2_ID,
                "scenario_id": manifest["scenario_id"],
                "partition": partition_name,
                "seed": seed,
                "threshold": threshold,
                "neural_weight": neural_weight,
                **_confusion(y, fused, threshold),
                **metrics,
                **_symbolic_summary(symbolic, neural_decision, y),
            })
            runtime_rows.append({
                "system_id": SYSTEM_B_V2_ID,
                "scenario_id": manifest["scenario_id"],
                "partition": partition_name,
                "seed": seed,
                "sample_count": len(y),
                "neural_inference_seconds_single_pass": neural_seconds,
                **timing,
            })

            bootstrap = stratified_bootstrap_indices(
                y,
                replicates=SYSTEM_B_CONFIG["validation"]["bootstrap_replicates"],
                random_state=(
                    SYSTEM_B_CONFIG["validation"]["bootstrap_random_state_base"]
                    + seed
                ),
            )
            for rule_index, rule in enumerate(rules):
                mask = symbolic["activation_matrix"][:, rule_index]
                quality = rule_quality(
                    mask,
                    y_true=y,
                    neural_decision=neural_decision,
                    consequent=rule.consequent,
                )
                stability = bootstrap_gate_stability(
                    mask,
                    y_true=y,
                    neural_decision=neural_decision,
                    consequent=rule.consequent,
                    bootstrap_indices=bootstrap,
                    min_support=SYSTEM_B_CONFIG["validation"]["min_support"],
                    min_covered=SYSTEM_B_CONFIG["validation"]["min_covered"],
                    min_precision=SYSTEM_B_CONFIG["validation"]["min_class_precision"],
                    min_fidelity=SYSTEM_B_CONFIG["validation"]["min_neural_fidelity"],
                )
                rule_rows.append({
                    "system_id": SYSTEM_B_V2_ID,
                    "scenario_id": manifest["scenario_id"],
                    "partition": partition_name,
                    "seed": seed,
                    "rule_id": rule.rule_id,
                    "lineage_id": rule.lineage_id,
                    "consequent": rule.consequent,
                    **quality,
                    "stability": stability,
                    "complexity": rule.complexity,
                    "activation_rate": float(np.mean(mask)),
                    **_imputation_diagnostic(
                        raw_X,
                        mask=mask,
                        rule=rule,
                        y_true=y,
                        neural_decision=neural_decision,
                    ),
                })

            for window_index, (start, stop) in enumerate(reporting_windows(len(y))):
                sy = y[start:stop]
                ss = fused[start:stop]
                s_symbolic = {
                    key: value[start:stop]
                    for key, value in symbolic.items()
                    if key != "activation_matrix"
                }
                window_rows.append({
                    "system_id": SYSTEM_B_V2_ID,
                    "scenario_id": manifest["scenario_id"],
                    "partition": partition_name,
                    "seed": seed,
                    "window_index": window_index,
                    "row_start": start,
                    "row_end": stop,
                    **_confusion(sy, ss, threshold),
                    **_safe_window_metrics(sy, ss, threshold),
                    **_symbolic_summary(
                        s_symbolic,
                        neural_decision[start:stop],
                        sy,
                    ),
                })
            del model, neural_prob, neural_decision, symbolic, fused
        del raw_X, X, y, partition

    metric_rows, aggregate_rows, paired_rows, aggregate_paired_rows = (
        _build_metric_tables(
            detection_rows,
            scenario_version=int(manifest["scenario_version"]),
            metric_names=V2_EVIDENCE_METRICS,
        )
    )
    staleness_rows = _rule_staleness_deltas(
        rule_rows,
        scenario_version=int(manifest["scenario_version"]),
        system_id=SYSTEM_B_V2_ID,
    )

    EVALUATION_DIR.mkdir(parents=True, exist_ok=False)
    paths = {
        "detection_by_seed": EVALUATION_DIR / "detection_by_seed.csv",
        "metrics_by_seed": EVALUATION_DIR / "metrics_by_seed.csv",
        "aggregate_metrics": EVALUATION_DIR / "aggregate_metrics.csv",
        "paired_deltas_by_seed": EVALUATION_DIR / "paired_deltas_by_seed.csv",
        "aggregate_paired_deltas": EVALUATION_DIR / "aggregate_paired_deltas.csv",
        "rule_quality": EVALUATION_DIR / "rule_quality_by_seed_partition.csv",
        "rule_staleness_deltas": EVALUATION_DIR / "rule_staleness_deltas.csv",
        "window_metrics": EVALUATION_DIR / "window_metrics.csv",
        "runtime": EVALUATION_DIR / "runtime_by_seed_partition.csv",
    }
    for path, rows in (
        (paths["detection_by_seed"], detection_rows),
        (paths["metrics_by_seed"], metric_rows),
        (paths["aggregate_metrics"], aggregate_rows),
        (paths["paired_deltas_by_seed"], paired_rows),
        (paths["aggregate_paired_deltas"], aggregate_paired_rows),
        (paths["rule_quality"], rule_rows),
        (paths["rule_staleness_deltas"], staleness_rows),
        (paths["window_metrics"], window_rows),
        (paths["runtime"], runtime_rows),
    ):
        _write_csv_new(path, rows)

    summary = {
        "evaluation_format_version": 1,
        "evaluation_id": EVALUATION_ID,
        "evidence_status": "implementation_defect_correction_not_first_look",
        "historical_v1_held_out_outcomes_known": True,
        "system_id": SYSTEM_B_V2_ID,
        "system_manifest_sha256": manifest["manifest_sha256"],
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "evaluation_git": evaluation_git,
        "runtime": runtime,
        "data_access": {
            "training_used": False,
            "development_used": False,
            "pre_drift_used": True,
            "post_drift_used": True,
        },
        "timing_protocol": {
            "symbolic_fusion_warmup_repeats": TIMING_WARMUP_REPEATS,
            "symbolic_fusion_measured_repeats": TIMING_MEASURED_REPEATS,
        },
        "rows": {
            "detection": len(detection_rows),
            "metrics_by_seed": len(metric_rows),
            "aggregate_metrics": len(aggregate_rows),
            "paired_deltas": len(paired_rows),
            "aggregate_paired_deltas": len(aggregate_paired_rows),
            "rule_quality": len(rule_rows),
            "rule_staleness_deltas": len(staleness_rows),
            "windows": len(window_rows),
            "runtime": len(runtime_rows),
        },
    }
    summary_path = EVALUATION_DIR / "system_b_v2_evaluation.json"
    _write_json_new(summary_path, summary)
    paths["summary"] = summary_path

    evaluation_manifest = {
        "manifest_format_version": 1,
        "evaluation_id": EVALUATION_ID,
        "evidence_status": "implementation_defect_correction_not_first_look",
        "system_id": SYSTEM_B_V2_ID,
        "system_manifest_sha256": manifest["manifest_sha256"],
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "evaluation_git": evaluation_git,
        "runtime": runtime,
        "files": {
            name: {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
            for name, path in paths.items()
        },
    }
    evaluation_manifest["manifest_sha256"] = canonical_json_hash(
        evaluation_manifest
    )
    _write_json_new(EVALUATION_MANIFEST_PATH, evaluation_manifest)
    print(f"evaluation_manifest={EVALUATION_MANIFEST_PATH}")
    print(f"evaluation_manifest_hash={evaluation_manifest['manifest_sha256']}")
    print("evidence_status=implementation_defect_correction_not_first_look")
    print("training_loaded=false")
    print("development_loaded=false")
    print("status=frozen_system_b_v2_corrected_evaluation_written")


def verify_r0_v2_evaluation() -> None:
    manifest = load_accepted_r0_v2_manifest()
    if not EVALUATION_MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"Missing corrected v2 evaluation manifest: {EVALUATION_MANIFEST_PATH}"
        )
    evaluation = json.loads(
        EVALUATION_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    stored = evaluation.get("manifest_sha256")
    core = dict(evaluation)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Corrected v2 evaluation manifest hash mismatch.")
    if evaluation.get("system_manifest_sha256") != manifest["manifest_sha256"]:
        raise ValueError("Corrected v2 evaluation references the wrong R0.v2.")
    if evaluation.get("evidence_status") != (
        "implementation_defect_correction_not_first_look"
    ):
        raise ValueError("Corrected v2 evaluation evidence-status mismatch.")
    for name, entry in evaluation["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing corrected v2 evaluation artifact {name!r}: {path}"
            )
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(
                f"Corrected v2 evaluation artifact hash mismatch for {name!r}."
            )
    print(f"evaluation_manifest={EVALUATION_MANIFEST_PATH}")
    print(f"evaluation_manifest_hash={stored}")
    print("source_r0_v2_verified=true")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
