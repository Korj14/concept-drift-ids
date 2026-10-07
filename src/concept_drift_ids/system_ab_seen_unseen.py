from __future__ import annotations

import json
from typing import Any

import numpy as np

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import mean_ci95, predict_probabilities
from concept_drift_ids.retrospective_scenario_audit import _training_seen_mask
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import canonical_json_hash, fuse_scores, infer_symbolic
from concept_drift_ids.system_a import (
    SYSTEM_A_CONFIG,
    _load_checkpoint_model,
    _load_frozen_system_a_manifest,
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
from concept_drift_ids.system_b_r0_v2 import load_accepted_r0_v2_manifest


ANALYSIS_ID = "system_ab_seen_unseen_exact_pattern_v1"
OUTPUT_DIR = PROJECT_ROOT / "results" / "robustness" / ANALYSIS_ID
MANIFEST_PATH = OUTPUT_DIR / "analysis_manifest.json"
ROWS_PATH = OUTPUT_DIR / "metrics_by_seed_stratum.csv"
AGGREGATE_PATH = OUTPUT_DIR / "aggregate_metrics.csv"
SUMMARY_PATH = OUTPUT_DIR / "analysis_summary.json"

METRICS = (
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
    "symbolic_neural_fidelity",
)


def _load_analysis_partitions():
    return (
        load_partition("training"),
        load_partition("pre_drift"),
        load_partition("post_drift"),
    )


def _load_rules(manifest: dict[str, Any], seed: int):
    entry = manifest["rule_artifacts"][str(seed)]
    payload = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
    return [_rule_from_dict(item) for item in payload["rules"]]


def _symbolic_subset(
    symbolic: dict[str, np.ndarray],
    neural_decision: np.ndarray,
    mask: np.ndarray,
) -> dict[str, float | None]:
    selected = np.asarray(mask, dtype=bool)
    covered = symbolic["covered"][selected]
    symbolic_class = symbolic["symbolic_class"][selected]
    neural = neural_decision[selected]
    return {
        "resolved_coverage": float(np.mean(covered)) if len(covered) else None,
        "symbolic_neural_fidelity": (
            float(np.mean(symbolic_class[covered] == neural[covered]))
            if np.any(covered)
            else None
        ),
    }


def _aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    groups = sorted(
        {
            (str(row["system_id"]), str(row["partition"]), str(row["stratum"]))
            for row in rows
        }
    )
    for system_id, partition, stratum in groups:
        selected = [
            row
            for row in rows
            if row["system_id"] == system_id
            and row["partition"] == partition
            and row["stratum"] == stratum
        ]
        for metric in METRICS:
            values = [
                float(row[metric])
                for row in selected
                if row.get(metric) is not None
            ]
            if not values:
                out.append({
                    "system_id": system_id,
                    "partition": partition,
                    "stratum": stratum,
                    "metric": metric,
                    "n_seeds": 0,
                    "mean": None,
                    "std": None,
                    "ci95_low": None,
                    "ci95_high": None,
                })
                continue
            summary = mean_ci95(np.asarray(values, dtype=np.float64))
            out.append({
                "system_id": system_id,
                "partition": partition,
                "stratum": stratum,
                "metric": metric,
                "n_seeds": len(values),
                **summary,
            })
    return out


def build_seen_unseen_analysis(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("Seen/unseen fixed-model rescore is frozen to CPU.")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Analysis already exists; refusing overwrite: {OUTPUT_DIR}")
    git = _git_state(require_clean=True)
    frozen_a = _load_frozen_system_a_manifest()
    manifest_b = load_accepted_r0_v2_manifest()
    preprocessing = load_frozen_preprocessing()

    training, pre, post = _load_analysis_partitions()
    seen_masks = {
        "pre_drift": _training_seen_mask(training.X, pre.X),
        "post_drift": _training_seen_mask(training.X, post.X),
    }
    partitions = {"pre_drift": pre, "post_drift": post}
    del training

    rows: list[dict[str, object]] = []
    stratum_counts: dict[str, dict[str, dict[str, int]]] = {}

    for partition_name, partition in partitions.items():
        seen = seen_masks[partition_name]
        y = partition.y.to_numpy(dtype=np.int8, copy=True)
        stratum_counts[partition_name] = {}
        for label, mask in (("seen", seen), ("unseen", ~seen)):
            stratum_counts[partition_name][label] = {
                "rows": int(np.sum(mask)),
                "benign": int(np.sum(mask & (y == 0))),
                "attack": int(np.sum(mask & (y == 1))),
            }

        X = transform_frame(partition.X, preprocessing, dtype=np.dtype("float32"))
        for seed in SYSTEM_B_CONFIG["seeds"]:
            record = next(
                row for row in frozen_a["seed_records"] if int(row["seed"]) == seed
            )
            model = _load_checkpoint_model(
                record,
                device=__import__("torch").device("cpu"),
                preprocessing_hash=preprocessing.state_hash,
            )
            neural_prob = predict_probabilities(
                model,
                X,
                device=__import__("torch").device("cpu"),
                batch_size=SYSTEM_A_CONFIG["batch_size"],
            )
            neural_decision = (
                neural_prob >= float(record["threshold"])
            ).astype(np.int8)
            rules = _load_rules(manifest_b, seed)
            symbolic = infer_symbolic(
                X,
                feature_names=preprocessing.feature_columns,
                rules=rules,
            )
            fused = fuse_scores(
                neural_prob,
                symbolic,
                neural_weight=float(manifest_b["fusion"]["selected_neural_weight"]),
            )
            threshold_b = float(
                manifest_b["fusion"]["per_seed_thresholds"][str(seed)]
            )

            for stratum, mask in (("seen", seen), ("unseen", ~seen)):
                sy = y[mask]
                if len(sy) == 0:
                    raise ValueError(f"Empty {partition_name}/{stratum} stratum.")
                a_metrics = _safe_window_metrics(
                    sy,
                    neural_prob[mask],
                    float(record["threshold"]),
                )
                rows.append({
                    "system_id": "system_a_static_neural_v1",
                    "partition": partition_name,
                    "stratum": stratum,
                    "seed": seed,
                    "sample_count": len(sy),
                    "benign_count": int(np.sum(sy == 0)),
                    "attack_count": int(np.sum(sy == 1)),
                    **_confusion(sy, neural_prob[mask], float(record["threshold"])),
                    **a_metrics,
                    "resolved_coverage": None,
                    "symbolic_neural_fidelity": None,
                })
                b_metrics = _safe_window_metrics(sy, fused[mask], threshold_b)
                rows.append({
                    "system_id": "system_b_static_neuro_symbolic_v2_corrected",
                    "partition": partition_name,
                    "stratum": stratum,
                    "seed": seed,
                    "sample_count": len(sy),
                    "benign_count": int(np.sum(sy == 0)),
                    "attack_count": int(np.sum(sy == 1)),
                    **_confusion(sy, fused[mask], threshold_b),
                    **b_metrics,
                    **_symbolic_subset(symbolic, neural_decision, mask),
                })
            del model, neural_prob, neural_decision, symbolic, fused

    aggregate = _aggregate(rows)
    summary = {
        "analysis_format_version": 1,
        "analysis_id": ANALYSIS_ID,
        "evidence_status": "posthoc_fixed_model_robustness_not_model_selection",
        "analysis_git": git,
        "system_a_manifest_sha256": frozen_a["manifest_sha256"],
        "system_b_v2_manifest_sha256": manifest_b["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "data_access": {
            "training_used_for_exact_pattern_membership_only": True,
            "development_used": False,
            "pre_drift_used": True,
            "post_drift_used": True,
        },
        "stratum_definition": (
            "Exact equality of the frozen 77-feature raw representation to at least "
            "one training-row feature vector, before median imputation/scaling."
        ),
        "stratum_counts": stratum_counts,
        "interpretation": (
            "This rescore is descriptive robustness after primary A/B outcomes are "
            "known. It does not alter checkpoints, R0.v2, fusion weights or thresholds."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    _write_csv_new(ROWS_PATH, rows)
    _write_csv_new(AGGREGATE_PATH, aggregate)
    summary["artifact_sha256"] = canonical_json_hash(summary)
    _write_json_new(SUMMARY_PATH, summary)
    manifest = {
        "manifest_format_version": 1,
        "analysis_id": ANALYSIS_ID,
        "summary_artifact_sha256": summary["artifact_sha256"],
        "files": {
            "rows": {
                "path": ROWS_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(ROWS_PATH),
            },
            "aggregate": {
                "path": AGGREGATE_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(AGGREGATE_PATH),
            },
            "summary": {
                "path": SUMMARY_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(SUMMARY_PATH),
            },
        },
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)

    print(f"analysis_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    for partition, counts in stratum_counts.items():
        print(
            f"{partition}_seen_rows={counts['seen']['rows']} "
            f"seen_attack_rows={counts['seen']['attack']} "
            f"unseen_rows={counts['unseen']['rows']}"
        )
    print("status=seen_unseen_analysis_written")


def verify_seen_unseen_analysis() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing seen/unseen analysis: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Seen/unseen analysis manifest hash mismatch.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing seen/unseen file {name!r}: {path}")
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Seen/unseen file hash mismatch for {name!r}.")
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    summary_hash = summary.get("artifact_sha256")
    core = dict(summary)
    core.pop("artifact_sha256", None)
    if canonical_json_hash(core) != summary_hash:
        raise ValueError("Seen/unseen summary canonical hash mismatch.")
    if summary_hash != manifest["summary_artifact_sha256"]:
        raise ValueError("Seen/unseen summary identity mismatch.")
    print(f"analysis_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("source_models_rerun_without_tuning=true")
    print("status=verified")
