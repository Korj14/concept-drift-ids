from __future__ import annotations

import json
from typing import Any

import numpy as np
import torch

from concept_drift_ids.frozen_preprocessing import (
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.neural import (
    binary_metrics,
    mean_ci95,
    predict_probabilities,
)
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import canonical_json_hash, fuse_scores, infer_symbolic
from concept_drift_ids.system_a import SYSTEM_A_CONFIG, _load_checkpoint_model
from concept_drift_ids.system_a_duplicate_robustness import (
    MANIFEST_PATH as TEACHER_MANIFEST_PATH,
    verify_pattern_dedup_teacher,
)
from concept_drift_ids.system_b import (
    SYSTEM_B_CONFIG,
    _confusion,
    _git_state,
    _rule_from_dict,
    _safe_window_metrics,
    _write_csv_new,
    _write_json_new,
)
from concept_drift_ids.system_b_dedup_teacher_robustness import (
    MANIFEST_PATH as R0_MANIFEST_PATH,
    verify_pattern_dedup_teacher_r0,
)
from concept_drift_ids.system_b_v2_evaluation import (
    V2_EVIDENCE_METRICS,
    _symbolic_summary,
)


EVALUATION_ID = "system_ab_pattern_dedup_training_chain_v1_evaluation"
OUTPUT_DIR = PROJECT_ROOT / "results" / "robustness" / EVALUATION_ID
MANIFEST_PATH = OUTPUT_DIR / "evaluation_manifest.json"
ROWS_PATH = OUTPUT_DIR / "metrics_by_seed_system.csv"
AGGREGATE_PATH = OUTPUT_DIR / "aggregate_metrics.csv"
PAIRED_PATH = OUTPUT_DIR / "aggregate_paired_deltas.csv"
SUMMARY_PATH = OUTPUT_DIR / "evaluation_summary.json"

ALT_A_ID = "system_a_pattern_dedup_training_v1"
ALT_B_ID = "system_b_pattern_dedup_teacher_r0_v1"
DETECTION_METRICS = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "f1",
    "fpr",
    "mcc",
    "roc_auc",
    "average_precision",
)


def _load_evaluation_partitions():
    return load_partition("pre_drift"), load_partition("post_drift")


def _teacher_record(manifest: dict[str, Any], seed: int) -> dict[str, Any]:
    records = [row for row in manifest["seed_records"] if int(row["seed"]) == seed]
    if len(records) != 1:
        raise ValueError(f"Expected one alternate-teacher record for seed {seed}.")
    return records[0]


def _load_rules(manifest: dict[str, Any], seed: int):
    entry = manifest["rule_artifacts"][str(seed)]
    payload = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
    if payload.get("artifact_sha256") != entry["artifact_sha256"]:
        raise ValueError(f"Alternate R0 artifact identity mismatch for seed {seed}.")
    return payload, [_rule_from_dict(row) for row in payload["rules"]]


def _aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for system_id in (ALT_A_ID, ALT_B_ID):
        metrics = DETECTION_METRICS if system_id == ALT_A_ID else V2_EVIDENCE_METRICS
        for partition in ("pre_drift", "post_drift"):
            selected = [
                row for row in rows
                if row["system_id"] == system_id and row["partition"] == partition
            ]
            for metric in metrics:
                values = [
                    float(row[metric])
                    for row in selected
                    if row.get(metric) is not None
                ]
                summary = mean_ci95(np.asarray(values, dtype=np.float64))
                out.append({
                    "system_id": system_id,
                    "partition": partition,
                    "metric": metric,
                    "n_seeds": len(values),
                    **summary,
                })
    return out


def _rectangularize_rows(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return deterministic CSV rows with the union of all observed fields."""
    if not rows:
        return rows
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for name in row:
            if name not in seen:
                seen.add(name)
                fieldnames.append(name)
    return [
        {name: row.get(name) for name in fieldnames}
        for row in rows
    ]


def _paired_deltas(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for system_id in (ALT_A_ID, ALT_B_ID):
        metrics = DETECTION_METRICS if system_id == ALT_A_ID else V2_EVIDENCE_METRICS
        for metric in metrics:
            deltas: list[float] = []
            for seed in SYSTEM_B_CONFIG["seeds"]:
                pre = next(
                    row for row in rows
                    if row["system_id"] == system_id
                    and row["partition"] == "pre_drift"
                    and int(row["seed"]) == int(seed)
                )
                post = next(
                    row for row in rows
                    if row["system_id"] == system_id
                    and row["partition"] == "post_drift"
                    and int(row["seed"]) == int(seed)
                )
                if pre.get(metric) is None or post.get(metric) is None:
                    continue
                deltas.append(float(post[metric]) - float(pre[metric]))
            summary = mean_ci95(np.asarray(deltas, dtype=np.float64))
            out.append({
                "system_id": system_id,
                "metric": metric,
                "contrast": "post_minus_pre",
                "n_seeds": len(deltas),
                **summary,
            })
    return out


def evaluate_pattern_dedup_training_chain(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("Pattern-dedup chain evaluation is frozen to CPU.")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Pattern-dedup chain evaluation already exists: {OUTPUT_DIR}")

    git = _git_state(require_clean=True)
    verify_pattern_dedup_teacher()
    verify_pattern_dedup_teacher_r0()
    teacher = json.loads(TEACHER_MANIFEST_PATH.read_text(encoding="utf-8"))
    r0 = json.loads(R0_MANIFEST_PATH.read_text(encoding="utf-8"))
    if r0["source_alternate_teacher_manifest_sha256"] != teacher["manifest_sha256"]:
        raise ValueError("Alternate R0 does not reference the frozen alternate teacher.")

    preprocessing = load_frozen_preprocessing()
    if teacher["preprocessing_state_hash"] != preprocessing.state_hash:
        raise ValueError("Alternate teacher references the wrong frozen preprocessing.")
    if r0["preprocessing_state_hash"] != preprocessing.state_hash:
        raise ValueError("Alternate R0 references the wrong frozen preprocessing.")

    pre, post = _load_evaluation_partitions()
    partitions = {"pre_drift": pre, "post_drift": post}
    device = torch.device("cpu")
    rows: list[dict[str, object]] = []

    for partition_name, partition in partitions.items():
        X = transform_frame(partition.X, preprocessing, dtype=np.dtype("float32"))
        y = partition.y.to_numpy(dtype=np.int8, copy=True)
        del partition

        for seed in SYSTEM_B_CONFIG["seeds"]:
            record = _teacher_record(teacher, seed)
            model = _load_checkpoint_model(
                record,
                device=device,
                preprocessing_hash=preprocessing.state_hash,
            )
            neural_prob = predict_probabilities(
                model,
                X,
                device=device,
                batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
            )
            neural_threshold = float(record["threshold"])
            neural_decision = (neural_prob >= neural_threshold).astype(np.int8)
            neural_metrics = binary_metrics(y, neural_prob, neural_threshold)
            rows.append({
                "system_id": ALT_A_ID,
                "partition": partition_name,
                "seed": int(seed),
                "threshold": neural_threshold,
                "neural_weight": 1.0,
                "sample_count": len(y),
                **_confusion(y, neural_prob, neural_threshold),
                **neural_metrics,
            })

            payload, rules = _load_rules(r0, seed)
            symbolic = infer_symbolic(
                X,
                feature_names=preprocessing.feature_columns,
                rules=rules,
            )
            weight = float(r0["fusion"]["selected_neural_weight"])
            threshold = float(r0["fusion"]["per_seed_thresholds"][str(seed)])
            if float(payload["selected_neural_weight"]) != weight:
                raise ValueError(f"Alternate R0 weight mismatch for seed {seed}.")
            if float(payload["fused_threshold"]) != threshold:
                raise ValueError(f"Alternate R0 threshold mismatch for seed {seed}.")
            fused = fuse_scores(neural_prob, symbolic, neural_weight=weight)
            rows.append({
                "system_id": ALT_B_ID,
                "partition": partition_name,
                "seed": int(seed),
                "threshold": threshold,
                "neural_weight": weight,
                "sample_count": len(y),
                **_confusion(y, fused, threshold),
                **_safe_window_metrics(y, fused, threshold),
                **_symbolic_summary(symbolic, neural_decision, y),
            })
            del model, neural_prob, neural_decision, symbolic, fused

        del X, y

    rows = _rectangularize_rows(rows)
    aggregate = _aggregate(rows)
    paired = _paired_deltas(rows)
    summary = {
        "evaluation_format_version": 1,
        "evaluation_id": EVALUATION_ID,
        "evidence_status": "posthoc_training_duplicate_chain_robustness_not_model_selection",
        "source_alternate_teacher_manifest_sha256": teacher["manifest_sha256"],
        "source_alternate_r0_manifest_sha256": r0["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "evaluation_git": git,
        "data_access": {
            "training_used": False,
            "development_used": False,
            "pre_drift_used": True,
            "post_drift_used": True,
        },
        "systems": {
            ALT_A_ID: {
                "role": "pattern_deduplicated_training_neural_teacher",
                "threshold_source": "frozen_alternate_teacher_development_MCC",
            },
            ALT_B_ID: {
                "role": "same_alternate_teacher_plus_frozen_alternate_R0",
                "selected_neural_weight": float(r0["fusion"]["selected_neural_weight"]),
                "threshold_source": "frozen_alternate_R0_development_fusion_slice_MCC",
            },
        },
        "interpretation_firewall": (
            "This held-out evaluation quantifies dependence of the A-to-R0-to-B chain "
            "on training-row multiplicity. It cannot replace accepted System A, R0.v2, "
            "or corrected System B based on held-out outcomes."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    _write_csv_new(ROWS_PATH, rows)
    _write_csv_new(AGGREGATE_PATH, aggregate)
    _write_csv_new(PAIRED_PATH, paired)
    summary["artifact_sha256"] = canonical_json_hash(summary)
    _write_json_new(SUMMARY_PATH, summary)
    manifest = {
        "manifest_format_version": 1,
        "evaluation_id": EVALUATION_ID,
        "source_alternate_teacher_manifest_sha256": teacher["manifest_sha256"],
        "source_alternate_r0_manifest_sha256": r0["manifest_sha256"],
        "files": {
            "rows": {
                "path": ROWS_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(ROWS_PATH),
            },
            "aggregate": {
                "path": AGGREGATE_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(AGGREGATE_PATH),
            },
            "paired_deltas": {
                "path": PAIRED_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(PAIRED_PATH),
            },
            "summary": {
                "path": SUMMARY_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(SUMMARY_PATH),
            },
        },
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)

    print(f"pattern_dedup_chain_evaluation_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"source_alternate_teacher_manifest_hash={teacher['manifest_sha256']}")
    print(f"source_alternate_r0_manifest_hash={r0['manifest_sha256']}")
    print("training_loaded=false")
    print("development_loaded=false")
    print("status=pattern_dedup_chain_evaluation_written")


def verify_pattern_dedup_training_chain_evaluation() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing pattern-dedup chain evaluation: {MANIFEST_PATH}")

    verify_pattern_dedup_teacher()
    verify_pattern_dedup_teacher_r0()
    teacher = json.loads(TEACHER_MANIFEST_PATH.read_text(encoding="utf-8"))
    r0 = json.loads(R0_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Pattern-dedup chain evaluation manifest hash mismatch.")
    if manifest.get("source_alternate_teacher_manifest_sha256") != teacher["manifest_sha256"]:
        raise ValueError("Pattern-dedup chain evaluation references wrong teacher.")
    if manifest.get("source_alternate_r0_manifest_sha256") != r0["manifest_sha256"]:
        raise ValueError("Pattern-dedup chain evaluation references wrong alternate R0.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Pattern-dedup chain evaluation artifact mismatch: {name}")

    print(f"pattern_dedup_chain_evaluation_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("source_alternate_teacher_verified=true")
    print("source_alternate_r0_verified=true")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
