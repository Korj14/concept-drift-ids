from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from concept_drift_ids.cd_analysis import (
    build_confirmatory_family,
    recovery_time,
)
from concept_drift_ids.cd_control_plane import (
    SYSTEM_A_MONITOR_THRESHOLDS,
    canonical_sha256,
    write_json_new,
)
from concept_drift_ids.cd_primary_adapter import (
    EXPECTED_PRE_ROWS,
    load_primary_stream,
)
from concept_drift_ids.cd_primary_config import (
    PRIMARY_OUTPUT_ROOT,
    PRIMARY_SEEDS,
    verify_primary_run_config_for_execution,
)
from concept_drift_ids.cd_primary_phase_a import verify_phase_a_seed
from concept_drift_ids.cd_primary_phase_b import (
    ARM_NAMES,
    _build_model_resolver,
    load_frozen_arm_trajectory,
    verify_phase_b_seed,
)
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_symbolic_evaluation import (
    FUSION_THRESHOLDS,
    PRIMARY_NEURAL_WEIGHT,
    SymbolicArmEvaluation,
    evaluate_dynamic_symbolic_trajectory,
    fused_threshold,
    macro_correct_symbolic_coverage,
    verify_lambda_one_negative_control,
)
from concept_drift_ids.frozen_preprocessing import (
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.neural import (
    binary_metrics,
    predict_probabilities,
)
from concept_drift_ids.scenario_loader import load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import fuse_scores, reporting_windows


PRIMARY_WEIGHTS = (0.50, 0.70, 0.90, 1.00)


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


def _phase_c_dir(seed: int) -> Path:
    return (
        PRIMARY_OUTPUT_ROOT
        / "phase_c_offline_evaluation"
        / f"seed-{seed}"
    )


def _phase_c_root() -> Path:
    return PRIMARY_OUTPUT_ROOT / "phase_c_offline_evaluation"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_verified_json(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError(f"JSON payload hash mismatch: {path}")
    return payload


def _confusion_counts(
    y_true: np.ndarray,
    decision: np.ndarray,
) -> dict[str, int]:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(decision, dtype=np.int8)
    return {
        "tp": int(np.sum((y == 1) & (p == 1))),
        "tn": int(np.sum((y == 0) & (p == 0))),
        "fp": int(np.sum((y == 0) & (p == 1))),
        "fn": int(np.sum((y == 1) & (p == 0))),
    }


def _safe_binary_metrics(
    y_true: np.ndarray,
    probability: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    probability = np.asarray(probability, dtype=np.float64)
    decision = (probability >= float(threshold)).astype(np.int8)
    counts = _confusion_counts(y, decision)
    benign = counts["tn"] + counts["fp"]
    result: dict[str, Any] = {
        "accuracy": float(accuracy_score(y, decision)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y, decision)
        ),
        "precision": float(
            precision_score(y, decision, zero_division=0)
        ),
        "recall": float(recall_score(y, decision, zero_division=0)),
        "f1": float(f1_score(y, decision, zero_division=0)),
        "fpr": (
            float(counts["fp"] / benign) if benign else None
        ),
        "mcc": float(matthews_corrcoef(y, decision)),
        "roc_auc": (
            float(roc_auc_score(y, probability))
            if len(np.unique(y)) == 2
            else None
        ),
        "average_precision": (
            float(average_precision_score(y, probability))
            if np.any(y == 1)
            else None
        ),
        **counts,
    }
    return result


def _safe_explanation(
    y_true: np.ndarray,
    *,
    symbolic_class: np.ndarray,
    covered: np.ndarray,
    uncovered: np.ndarray,
    conflict: np.ndarray,
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    symbolic_class = np.asarray(symbolic_class, dtype=np.int8)
    covered = np.asarray(covered, dtype=bool)
    out: dict[str, Any] = {}
    correct_components: list[float] = []
    for value, name in ((0, "benign"), (1, "attack")):
        class_mask = y == value
        denominator = int(class_mask.sum())
        out[f"{name}_rows"] = denominator
        if denominator == 0:
            out[f"{name}_coverage"] = None
            out[f"{name}_symbolic_correctness_on_covered"] = None
            out[f"{name}_correct_symbolic_coverage"] = None
            continue
        class_covered = class_mask & covered
        resolved_correct = class_covered & (symbolic_class == value)
        coverage = float(class_covered.sum() / denominator)
        correctness = (
            float(
                np.mean(
                    symbolic_class[class_covered] == value
                )
            )
            if np.any(class_covered)
            else 0.0
        )
        correct = float(resolved_correct.sum() / denominator)
        out[f"{name}_coverage"] = coverage
        out[f"{name}_symbolic_correctness_on_covered"] = correctness
        out[f"{name}_correct_symbolic_coverage"] = correct
        correct_components.append(correct)
    out["mcsc"] = (
        float(np.mean(correct_components))
        if len(correct_components) == 2
        else None
    )
    out["resolved_coverage"] = float(np.mean(covered))
    out["uncovered_rate"] = float(np.mean(uncovered))
    out["conflict_abstain_rate"] = float(np.mean(conflict))
    return out


def _symbolic_payload(
    evaluation: SymbolicArmEvaluation,
) -> dict[str, np.ndarray]:
    return {
        "p_rule_attack": evaluation.symbolic_attack_probability,
        "symbolic_class": evaluation.symbolic_class,
        "covered": evaluation.covered,
        "uncovered": evaluation.uncovered,
        "conflict_abstain": evaluation.conflict_abstain,
    }


def _evaluation_for_weight(
    *,
    seed: int,
    base: SymbolicArmEvaluation,
    y_true: np.ndarray,
    weight: float,
) -> SymbolicArmEvaluation:
    symbolic = _symbolic_payload(base)
    fused = fuse_scores(
        base.neural_probability,
        symbolic,
        neural_weight=float(weight),
    )
    threshold = fused_threshold(seed=seed, neural_weight=weight)
    decision = (fused >= threshold).astype(np.int8)
    return SymbolicArmEvaluation(
        neural_probability=base.neural_probability,
        symbolic_attack_probability=base.symbolic_attack_probability,
        symbolic_class=base.symbolic_class,
        covered=base.covered,
        uncovered=base.uncovered,
        conflict_abstain=base.conflict_abstain,
        fused_probability=fused,
        thresholded_decision=decision,
        metrics=binary_metrics(y_true, fused, threshold),
        explanation=base.explanation,
    )


def _domain_slice(
    domain: str,
    n_rows: int,
) -> slice:
    if domain == "full":
        return slice(0, n_rows)
    if domain == "pre":
        return slice(0, EXPECTED_PRE_ROWS)
    if domain == "post":
        return slice(EXPECTED_PRE_ROWS, n_rows)
    raise ValueError(f"Unknown evaluation domain: {domain}")


def _metrics_by_domain(
    *,
    y: np.ndarray,
    probability: np.ndarray,
    decision: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for domain in ("full", "pre", "post"):
        s = _domain_slice(domain, len(y))
        metrics = _safe_binary_metrics(
            y[s],
            probability[s],
            threshold,
        )
        expected = _confusion_counts(y[s], decision[s])
        for key, value in expected.items():
            if metrics[key] != value:
                raise AssertionError("Decision/confusion mismatch.")
        out[domain] = metrics
    return out


def _explanation_by_domain(
    *,
    y: np.ndarray,
    evaluation: SymbolicArmEvaluation,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for domain in ("full", "pre", "post"):
        s = _domain_slice(domain, len(y))
        out[domain] = _safe_explanation(
            y[s],
            symbolic_class=evaluation.symbolic_class[s],
            covered=evaluation.covered[s],
            uncovered=evaluation.uncovered[s],
            conflict=evaluation.conflict_abstain[s],
        )
    return out


def _window_summaries(
    *,
    y: np.ndarray,
    evaluation: SymbolicArmEvaluation,
    threshold: float,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"pre": [], "post": []}
    for domain, start, stop in (
        ("pre", 0, EXPECTED_PRE_ROWS),
        ("post", EXPECTED_PRE_ROWS, len(y)),
    ):
        for local_start, local_stop in reporting_windows(stop - start):
            absolute_start = start + local_start
            absolute_stop = start + local_stop
            s = slice(absolute_start, absolute_stop)
            detection = _safe_binary_metrics(
                y[s],
                evaluation.fused_probability[s],
                threshold,
            )
            explanation = _safe_explanation(
                y[s],
                symbolic_class=evaluation.symbolic_class[s],
                covered=evaluation.covered[s],
                uncovered=evaluation.uncovered[s],
                conflict=evaluation.conflict_abstain[s],
            )
            out[domain].append(
                {
                    "start_index": absolute_start,
                    "end_index_exclusive": absolute_stop,
                    "row_count": absolute_stop - absolute_start,
                    "mcc": detection["mcc"],
                    "fpr": detection["fpr"],
                    "f1": detection["f1"],
                    "mcsc": explanation["mcsc"],
                    "resolved_coverage": explanation[
                        "resolved_coverage"
                    ],
                    "conflict_abstain_rate": explanation[
                        "conflict_abstain_rate"
                    ],
                }
            )
    return out


def _recovery_summary(
    windows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    specs = {
        "mcc": True,
        "mcsc": True,
        "fpr": False,
    }
    for metric, higher in specs.items():
        pre = list(windows["pre"])
        post = list(windows["post"])
        values = [
            item.get(metric) for item in (*pre[-3:], *post)
        ]
        if any(value is None for value in values):
            out[metric] = {
                "available": False,
                "reason": "undefined_window_metric",
            }
            continue
        result = recovery_time(
            pre,
            post,
            metric_key=metric,
            higher_is_better=higher,
            stream_end_index=EXPECTED_PRE_ROWS + sum(
                int(item["row_count"]) for item in windows["post"]
            ),
        )
        out[metric] = {"available": True, **result}
    return out


def _rule_version_ids(
    trajectory: Any,
    n_rows: int,
) -> list[str]:
    result = [trajectory.initial_state.rule_base_version_id] * n_rows
    for effective, state in sorted(
        trajectory.publications,
        key=lambda item: item[0],
    ):
        effective = int(effective)
        if not 0 <= effective <= n_rows:
            raise ValueError("Symbolic publication lies outside stream.")
        result[effective:] = [state.rule_base_version_id] * (
            n_rows - effective
        )
    return result


def _write_trace_gzip_new(
    path: Path,
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, str]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite trace: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    content_digest = hashlib.sha256()
    with path.open("xb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            compresslevel=9,
            mtime=0,
        ) as compressed:
            for row in rows:
                line = (
                    json.dumps(
                        dict(row),
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    + "\n"
                ).encode("utf-8")
                content_digest.update(line)
                compressed.write(line)
    return {
        "sha256": sha256_file(path),
        "canonical_jsonl_sha256": content_digest.hexdigest(),
    }


def _trigger_diagnostics(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    drift = sorted(
        (
            event
            for event in events
            if event.get("event_type") == "drift_event"
            and event.get("status") == "confirmed"
        ),
        key=lambda item: int(item["logical_clock"]),
    )
    pre = [
        int(item["logical_clock"])
        for item in drift
        if int(item["logical_clock"]) < EXPECTED_PRE_ROWS
    ]
    post = [
        int(item["logical_clock"])
        for item in drift
        if int(item["logical_clock"]) >= EXPECTED_PRE_ROWS
    ]
    first_post = post[0] if post else None
    publications = [
        event
        for event in events
        if event.get("event_type") == "neural_publication"
        and event.get("status") == "published"
    ]
    return {
        "detector_event_count": len(drift),
        "pre_reference_alarm_count": len(pre),
        "pre_reference_alarm_clocks": pre,
        "post_reference_event_count": len(post),
        "first_post_reference_confirmation_clock": first_post,
        "first_post_reference_confirmation_delay_rows": (
            first_post - EXPECTED_PRE_ROWS
            if first_post is not None
            else None
        ),
        "latency_adjusted_excess_delay_rows": (
            first_post - (EXPECTED_PRE_ROWS + 5_000)
            if first_post is not None
            else None
        ),
        "repeated_post_reference_events": max(0, len(post) - 1),
        "neural_publication_count": len(publications),
    }


def _retention_probes(
    *,
    seed: int,
    checkpoint_chain: Sequence[Mapping[str, Any]],
    phase_a_dir: Path,
    X_pre: np.ndarray,
    y_pre: np.ndarray,
) -> list[dict[str, Any]]:
    preprocessing = load_frozen_preprocessing()
    development = load_partition("development")
    X_dev = transform_frame(
        development.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    del development
    resolver = _build_model_resolver(
        seed,
        phase_a_dir=phase_a_dir,
        checkpoint_chain=checkpoint_chain,
    )
    threshold = float(SYSTEM_A_MONITOR_THRESHOLDS[seed])
    rows: list[dict[str, Any]] = []
    best_so_far: dict[str, float] = {}
    initial_metrics: dict[str, float] | None = None

    for record in checkpoint_chain:
        checkpoint_sha = str(record["checkpoint_file_sha256"])
        model = resolver(checkpoint_sha)
        dev_probability = predict_probabilities(
            model,
            X_dev,
            device=np_to_cpu_device(),
            batch_size=4_096,
        )
        pre_probability = predict_probabilities(
            model,
            X_pre,
            device=np_to_cpu_device(),
            batch_size=4_096,
        )
        dev_metrics = binary_metrics(y_dev, dev_probability, threshold)
        pre_metrics = binary_metrics(y_pre, pre_probability, threshold)
        combined = {
            f"development_{key}": float(value)
            for key, value in dev_metrics.items()
        }
        combined.update(
            {
                f"pre_reference_{key}": float(value)
                for key, value in pre_metrics.items()
            }
        )
        if initial_metrics is None:
            initial_metrics = dict(combined)
        retention: dict[str, Any] = {}
        for key, value in combined.items():
            if key.endswith("_fpr"):
                previous_best = best_so_far.get(key, value)
                forgetting = value - min(previous_best, value)
                best_so_far[key] = min(previous_best, value)
            else:
                previous_best = best_so_far.get(key, value)
                forgetting = max(previous_best, value) - value
                best_so_far[key] = max(previous_best, value)
            retention[key] = {
                "value": value,
                "delta_from_initial": value - initial_metrics[key],
                "descriptive_forgetting": float(forgetting),
            }
        rows.append(
            {
                "sequence": int(record["sequence"]),
                "checkpoint_file_sha256": checkpoint_sha,
                "publication_effective_index": int(
                    record["publication_effective_index"]
                ),
                "metrics": retention,
            }
        )
    return rows


def np_to_cpu_device():
    import torch

    return torch.device("cpu")


def _arm_manifest(seed: int, arm: str) -> dict[str, Any]:
    path = _phase_b_dir(seed) / arm / "arm_manifest.json"
    return _read_verified_json(path)


def execute_phase_c_seed(seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported primary seed: {seed}")
    config = verify_primary_run_config_for_execution()
    configure_torch_primary_runtime()

    # Evaluation is allowed only after every adaptive trajectory is frozen.
    phase_a_verified = {
        other: verify_phase_a_seed(other) for other in PRIMARY_SEEDS
    }
    phase_b_verified = {
        other: verify_phase_b_seed(other) for other in PRIMARY_SEEDS
    }

    output_dir = _phase_c_dir(seed)
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to reuse existing Phase-C output: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=False)

    write_json_new(
        output_dir / "attempt.json",
        {
            "seed": seed,
            "primary_config_manifest_sha256": config["manifest_sha256"],
            "phase": "offline_boundary_aware_evaluation",
            "adaptive_components_received_boundary": False,
        },
    )

    try:
        phase_a_dir = _phase_a_dir(seed)
        predictions = read_jsonl(phase_a_dir / "predictions.jsonl")
        events = read_jsonl(phase_a_dir / "events.jsonl")
        checkpoint_chain = read_jsonl(
            phase_a_dir / "checkpoint_chain.jsonl"
        )
        preprocessing = load_frozen_preprocessing()
        stream_rows = load_primary_stream(preprocessing=preprocessing)
        X = np.stack(
            [np.asarray(row.features, dtype=np.float32) for row in stream_rows]
        )
        y = np.asarray(
            [int(row.label) for row in stream_rows],
            dtype=np.int8,
        )
        neural_probability = np.asarray(
            [float(item["neural_probability"]) for item in predictions],
            dtype=np.float64,
        )
        checkpoint_ids = [
            str(item["checkpoint_sha256"]) for item in predictions
        ]
        if len(X) != int(config["scenario"]["stream_rows"]):
            raise ValueError("Phase-C stream length differs from frozen config.")

        arm_summaries: dict[str, Any] = {}
        lambda_one_evaluations: dict[str, SymbolicArmEvaluation] = {}

        for arm in ARM_NAMES:
            trajectory = load_frozen_arm_trajectory(seed, arm)
            base = evaluate_dynamic_symbolic_trajectory(
                seed=seed,
                X=X,
                y_true=y,
                neural_probability=neural_probability,
                feature_names=preprocessing.feature_columns,
                trajectory=trajectory,
                neural_weight=PRIMARY_NEURAL_WEIGHT,
            )
            explanation = _explanation_by_domain(y=y, evaluation=base)
            evaluations: dict[float, SymbolicArmEvaluation] = {
                PRIMARY_NEURAL_WEIGHT: base
            }
            for weight in PRIMARY_WEIGHTS:
                if weight == PRIMARY_NEURAL_WEIGHT:
                    continue
                evaluations[weight] = _evaluation_for_weight(
                    seed=seed,
                    base=base,
                    y_true=y,
                    weight=weight,
                )
            lambda_one_evaluations[arm] = evaluations[1.0]

            metrics_by_weight: dict[str, Any] = {}
            for weight in PRIMARY_WEIGHTS:
                evaluation = evaluations[weight]
                threshold = fused_threshold(
                    seed=seed,
                    neural_weight=weight,
                )
                metrics_by_weight[str(weight)] = _metrics_by_domain(
                    y=y,
                    probability=evaluation.fused_probability,
                    decision=evaluation.thresholded_decision,
                    threshold=threshold,
                )

            primary_threshold = fused_threshold(
                seed=seed,
                neural_weight=PRIMARY_NEURAL_WEIGHT,
            )
            windows = _window_summaries(
                y=y,
                evaluation=base,
                threshold=primary_threshold,
            )
            recovery = _recovery_summary(windows)
            rule_versions = _rule_version_ids(trajectory, len(y))

            def trace_rows():
                for index in range(len(y)):
                    symbolic_probability = (
                        None
                        if np.isnan(base.symbolic_attack_probability[index])
                        else float(base.symbolic_attack_probability[index])
                    )
                    row: dict[str, Any] = {
                        "row_id": stream_rows[index].row_id,
                        "origin_index": index,
                        "true_label": int(y[index]),
                        "neural_checkpoint_sha256": checkpoint_ids[index],
                        "rule_base_version_id": rule_versions[index],
                        "neural_probability": float(
                            neural_probability[index]
                        ),
                        "symbolic_attack_probability": symbolic_probability,
                        "symbolic_class": int(base.symbolic_class[index]),
                        "covered": bool(base.covered[index]),
                        "uncovered": bool(base.uncovered[index]),
                        "conflict_abstain": bool(
                            base.conflict_abstain[index]
                        ),
                    }
                    for weight in PRIMARY_WEIGHTS:
                        key = str(weight).replace(".", "_")
                        evaluation = evaluations[weight]
                        row[f"fused_probability_lambda_{key}"] = float(
                            evaluation.fused_probability[index]
                        )
                        row[f"decision_lambda_{key}"] = int(
                            evaluation.thresholded_decision[index]
                        )
                    yield row

            trace_path = output_dir / f"{arm}_prediction_trace.jsonl.gz"
            trace_identity = _write_trace_gzip_new(
                trace_path,
                trace_rows(),
            )

            arm_manifest = _arm_manifest(seed, arm)
            summary = {
                "seed": seed,
                "arm": arm,
                "primary_config_manifest_sha256": config["manifest_sha256"],
                "phase_b_arm_manifest_sha256": arm_manifest[
                    "manifest_sha256"
                ],
                "shared_identity_sha256": trajectory.shared_identity_sha256,
                "metrics_by_neural_weight": metrics_by_weight,
                "explanation": explanation,
                "primary_windows": windows,
                "primary_recovery": recovery,
                "maintenance_summary": arm_manifest[
                    "maintenance_summary"
                ],
                "prediction_trace": {
                    "path": trace_path.name,
                    **trace_identity,
                },
            }
            summary["summary_sha256"] = canonical_sha256(summary)
            write_json_new(
                output_dir / f"{arm}_evaluation.json",
                summary,
            )
            arm_summaries[arm] = summary

        verify_lambda_one_negative_control(
            lambda_one_evaluations["c_frozen_symbolic"],
            lambda_one_evaluations["d_drift"],
        )
        verify_lambda_one_negative_control(
            lambda_one_evaluations["c_frozen_symbolic"],
            lambda_one_evaluations["d_periodic"],
        )

        X_pre = X[:EXPECTED_PRE_ROWS]
        y_pre = y[:EXPECTED_PRE_ROWS]
        retention = _retention_probes(
            seed=seed,
            checkpoint_chain=checkpoint_chain,
            phase_a_dir=phase_a_dir,
            X_pre=X_pre,
            y_pre=y_pre,
        )
        trigger = _trigger_diagnostics(events)
        seed_manifest = {
            "schema_version": 1,
            "seed": seed,
            "status": "complete_offline_evaluation",
            "primary_config_manifest_sha256": config["manifest_sha256"],
            "phase_a_run_manifest_sha256": phase_a_verified[seed][
                "run_manifest_sha256"
            ],
            "phase_b_seed_manifest_sha256": phase_b_verified[seed][
                "phase_b_manifest_sha256"
            ],
            "arm_summary_sha256": {
                arm: summary["summary_sha256"]
                for arm, summary in arm_summaries.items()
            },
            "lambda_one_predictive_equality": True,
            "trigger_diagnostics": trigger,
            "neural_retention_probes": retention,
            "boundary_index": EXPECTED_PRE_ROWS,
            "adaptive_components_received_boundary": False,
        }
        seed_manifest["manifest_sha256"] = canonical_sha256(seed_manifest)
        write_json_new(
            output_dir / "phase_c_seed_manifest.json",
            seed_manifest,
        )
        verified = verify_phase_c_seed(seed)
        return {
            "status": "phase_c_seed_complete",
            "seed": seed,
            "phase_c_manifest_sha256": verified[
                "phase_c_manifest_sha256"
            ],
            "lambda_one_predictive_equality": True,
        }

    except Exception as exc:
        failure_path = output_dir / "failure.json"
        if not failure_path.exists():
            write_json_new(
                failure_path,
                {
                    "seed": seed,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "phase": "offline_boundary_aware_evaluation",
                    "adaptive_components_received_boundary": False,
                },
            )
        raise


def verify_phase_c_seed(seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported primary seed: {seed}")
    config = verify_primary_run_config_for_execution()
    output_dir = _phase_c_dir(seed)
    manifest = _read_verified_json(
        output_dir / "phase_c_seed_manifest.json"
    )
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError("Phase-C seed manifest canonical hash mismatch.")
    if int(manifest["seed"]) != seed:
        raise ValueError("Phase-C seed mismatch.")
    if manifest["primary_config_manifest_sha256"] != config[
        "manifest_sha256"
    ]:
        raise ValueError("Phase-C seed references wrong primary config.")
    phase_a = verify_phase_a_seed(seed)
    phase_b = verify_phase_b_seed(seed)
    if (
        manifest["phase_a_run_manifest_sha256"]
        != phase_a["run_manifest_sha256"]
    ):
        raise ValueError("Phase-C seed Phase-A identity mismatch.")
    if (
        manifest["phase_b_seed_manifest_sha256"]
        != phase_b["phase_b_manifest_sha256"]
    ):
        raise ValueError("Phase-C seed Phase-B identity mismatch.")
    if manifest["lambda_one_predictive_equality"] is not True:
        raise ValueError("Phase-C lambda=1 negative control failed.")
    if manifest["adaptive_components_received_boundary"] is not False:
        raise ValueError("Boundary-contamination flag is not false.")

    for arm in ARM_NAMES:
        path = output_dir / f"{arm}_evaluation.json"
        summary = _read_verified_json(path)
        stored_summary = summary.pop("summary_sha256", None)
        if stored_summary != canonical_sha256(summary):
            raise ValueError("Arm evaluation summary hash mismatch.")
        if stored_summary != manifest["arm_summary_sha256"][arm]:
            raise ValueError("Phase-C arm summary identity mismatch.")
        trace = summary["prediction_trace"]
        trace_path = output_dir / trace["path"]
        if sha256_file(trace_path) != trace["sha256"]:
            raise ValueError("Phase-C prediction trace file hash mismatch.")
        content_digest = hashlib.sha256()
        with gzip.open(trace_path, "rb") as file:
            while True:
                chunk = file.read(1024 * 1024)
                if not chunk:
                    break
                content_digest.update(chunk)
        if (
            content_digest.hexdigest()
            != trace["canonical_jsonl_sha256"]
        ):
            raise ValueError(
                "Phase-C prediction trace content identity mismatch."
            )

    return {
        "status": "phase_c_seed_verified",
        "seed": seed,
        "phase_c_manifest_sha256": stored,
        "lambda_one_predictive_equality": True,
    }


def verify_primary_aggregate() -> dict[str, Any]:
    config = verify_primary_run_config_for_execution()
    path = _phase_c_root() / "confirmatory_analysis.json"
    payload = _read_verified_json(path)
    stored = payload.pop("manifest_sha256", None)
    if stored != canonical_sha256(payload):
        raise ValueError("Confirmatory aggregate manifest hash mismatch.")
    if payload["primary_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Confirmatory aggregate references wrong config.")
    if payload["lambda_one_predictive_equality_all_seeds"] is not True:
        raise ValueError("Confirmatory aggregate failed lambda=1 control.")
    expected = {
        str(seed): verify_phase_c_seed(seed)["phase_c_manifest_sha256"]
        for seed in PRIMARY_SEEDS
    }
    if payload["seed_manifest_sha256"] != expected:
        raise ValueError("Confirmatory aggregate seed identities changed.")
    return {
        "status": "primary_confirmatory_aggregate_verified",
        "manifest_sha256": stored,
        "seed_count": len(PRIMARY_SEEDS),
    }


def build_primary_aggregate() -> dict[str, Any]:
    config = verify_primary_run_config_for_execution()
    configure_torch_primary_runtime()
    seed_manifests = {
        seed: verify_phase_c_seed(seed) for seed in PRIMARY_SEEDS
    }
    output_path = _phase_c_root() / "confirmatory_analysis.json"
    if output_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite confirmatory analysis: {output_path}"
        )

    summaries: dict[int, dict[str, dict[str, Any]]] = {}
    for seed in PRIMARY_SEEDS:
        summaries[seed] = {
            arm: _read_verified_json(
                _phase_c_dir(seed) / f"{arm}_evaluation.json"
            )
            for arm in ARM_NAMES
        }

    def post_mcc(seed: int, arm: str) -> float:
        return float(
            summaries[seed][arm]["metrics_by_neural_weight"]["0.5"][
                "post"
            ]["mcc"]
        )

    def post_mcsc(seed: int, arm: str) -> float:
        return float(
            summaries[seed][arm]["explanation"]["post"]["mcsc"]
        )

    family = build_confirmatory_family(
        d_drift_mcc_by_seed={
            seed: post_mcc(seed, "d_drift") for seed in PRIMARY_SEEDS
        },
        c_mcc_by_seed={
            seed: post_mcc(seed, "c_frozen_symbolic")
            for seed in PRIMARY_SEEDS
        },
        d_drift_mcsc_by_seed={
            seed: post_mcsc(seed, "d_drift") for seed in PRIMARY_SEEDS
        },
        c_mcsc_by_seed={
            seed: post_mcsc(seed, "c_frozen_symbolic")
            for seed in PRIMARY_SEEDS
        },
        d_periodic_mcsc_by_seed={
            seed: post_mcsc(seed, "d_periodic")
            for seed in PRIMARY_SEEDS
        },
    )
    payload = {
        "schema_version": 1,
        "status": "complete_prespecified_five_seed_confirmatory_family",
        "primary_config_manifest_sha256": config["manifest_sha256"],
        "seed_manifest_sha256": {
            str(seed): seed_manifests[seed]["phase_c_manifest_sha256"]
            for seed in PRIMARY_SEEDS
        },
        "confirmatory_family": family,
        "lambda_one_predictive_equality_all_seeds": True,
        "inferential_scope": (
            "stochastic_seed_variation_conditional_on_fixed_primary_scenario"
        ),
        "windows_or_rules_treated_as_independent_replicates": False,
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    write_json_new(output_path, payload)
    return {
        "status": "primary_confirmatory_aggregate_written",
        "manifest_sha256": payload["manifest_sha256"],
        "seed_count": len(PRIMARY_SEEDS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Offline primary C/D evaluation. Requires all five Phase-A and "
            "Phase-B trajectories frozen before any boundary-aware scoring."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", type=int, choices=PRIMARY_SEEDS)
    group.add_argument("--aggregate", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.aggregate:
        if args.verify_only:
            raise ValueError("--verify-only is not valid with --aggregate.")
        result = build_primary_aggregate()
    else:
        result = (
            verify_phase_c_seed(args.seed)
            if args.verify_only
            else execute_phase_c_seed(args.seed)
        )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
