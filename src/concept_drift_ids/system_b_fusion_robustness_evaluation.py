from __future__ import annotations

import json
from typing import Any

import numpy as np
import torch

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import mean_ci95, predict_probabilities
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
    _record_for_seed,
    _rule_from_dict,
    _safe_window_metrics,
    _write_csv_new,
    _write_json_new,
)
from concept_drift_ids.system_b_fusion_robustness import (
    MANIFEST_PATH as SELECTION_MANIFEST_PATH,
    SENSITIVITY_WEIGHTS,
    verify_fusion_authority_selection,
)
from concept_drift_ids.system_b_r0_v2 import load_accepted_r0_v2_manifest
from concept_drift_ids.system_b_v2_evaluation import (
    V2_EVIDENCE_METRICS,
    _symbolic_summary,
)


EVALUATION_ID = "system_b_fusion_authority_v1_evaluation"
OUTPUT_DIR = PROJECT_ROOT / "results" / "robustness" / EVALUATION_ID
MANIFEST_PATH = OUTPUT_DIR / "evaluation_manifest.json"
ROWS_PATH = OUTPUT_DIR / "metrics_by_seed_weight.csv"
AGGREGATE_PATH = OUTPUT_DIR / "aggregate_metrics.csv"
SUMMARY_PATH = OUTPUT_DIR / "evaluation_summary.json"


def _load_evaluation_partitions():
    return load_partition("pre_drift"), load_partition("post_drift")


def _load_rules(manifest: dict[str, Any], seed: int):
    entry = manifest["rule_artifacts"][str(seed)]
    payload = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
    return [_rule_from_dict(row) for row in payload["rules"]]


def _aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for weight in SENSITIVITY_WEIGHTS:
        for partition in ("pre_drift", "post_drift"):
            selected = [
                row for row in rows
                if float(row["neural_weight"]) == float(weight)
                and row["partition"] == partition
            ]
            for metric in V2_EVIDENCE_METRICS:
                values = [
                    float(row[metric])
                    for row in selected
                    if row.get(metric) is not None
                ]
                summary = mean_ci95(np.asarray(values, dtype=np.float64))
                out.append({
                    "neural_weight": float(weight),
                    "partition": partition,
                    "metric": metric,
                    "n_seeds": len(values),
                    **summary,
                })
    return out


def evaluate_fusion_authority(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("Fusion-authority held-out sensitivity is frozen to CPU.")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Fusion-authority evaluation already exists: {OUTPUT_DIR}")

    git = _git_state(require_clean=True)
    verify_fusion_authority_selection()
    selection = json.loads(SELECTION_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_b = load_accepted_r0_v2_manifest()
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    pre, post = _load_evaluation_partitions()
    partitions = {"pre_drift": pre, "post_drift": post}

    rows: list[dict[str, object]] = []
    for partition_name, partition in partitions.items():
        X = transform_frame(partition.X, preprocessing, dtype=np.dtype("float32"))
        y = partition.y.to_numpy(dtype=np.int8, copy=True)
        for seed in SYSTEM_B_CONFIG["seeds"]:
            record = _record_for_seed(frozen_a, seed)
            model = _load_checkpoint_model(
                record,
                device=torch.device("cpu"),
                preprocessing_hash=preprocessing.state_hash,
            )
            neural_prob = predict_probabilities(
                model,
                X,
                device=torch.device("cpu"),
                batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
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
            for weight in SENSITIVITY_WEIGHTS:
                threshold = float(
                    selection["per_weight_seed_thresholds"][f"{weight:.2f}"][
                        str(seed)
                    ]
                )
                fused = fuse_scores(
                    neural_prob,
                    symbolic,
                    neural_weight=float(weight),
                )
                rows.append({
                    "system_id": "system_b_static_neuro_symbolic_v2_corrected",
                    "partition": partition_name,
                    "seed": int(seed),
                    "neural_weight": float(weight),
                    "threshold": threshold,
                    "sample_count": len(y),
                    **_confusion(y, fused, threshold),
                    **_safe_window_metrics(y, fused, threshold),
                    **_symbolic_summary(symbolic, neural_decision, y),
                })
            del model, neural_prob, neural_decision, symbolic

    aggregate = _aggregate(rows)
    summary = {
        "evaluation_format_version": 1,
        "evaluation_id": EVALUATION_ID,
        "evidence_status": "posthoc_fusion_authority_robustness_not_model_selection",
        "selection_manifest_sha256": selection["manifest_sha256"],
        "source_system_b_v2_manifest_sha256": manifest_b["manifest_sha256"],
        "evaluation_git": git,
        "data_access": {
            "training_used": False,
            "development_used": False,
            "pre_drift_used": True,
            "post_drift_used": True,
        },
        "interpretation_firewall": (
            "Sensitivity outcomes quantify dependence on symbolic/neural authority. "
            "They cannot replace the accepted lambda=0.50 R0.v2 baseline."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    _write_csv_new(ROWS_PATH, rows)
    _write_csv_new(AGGREGATE_PATH, aggregate)
    summary["artifact_sha256"] = canonical_json_hash(summary)
    _write_json_new(SUMMARY_PATH, summary)
    manifest = {
        "manifest_format_version": 1,
        "evaluation_id": EVALUATION_ID,
        "selection_manifest_sha256": selection["manifest_sha256"],
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
    print(f"fusion_authority_evaluation_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print("training_loaded=false")
    print("development_loaded=false")
    print("status=fusion_authority_evaluation_written")


def verify_fusion_authority_evaluation() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing fusion-authority evaluation: {MANIFEST_PATH}")
    verify_fusion_authority_selection()
    selection = json.loads(SELECTION_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Fusion-authority evaluation manifest hash mismatch.")
    if manifest.get("selection_manifest_sha256") != selection["manifest_sha256"]:
        raise ValueError("Fusion-authority evaluation references wrong selection.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Fusion-authority evaluation artifact mismatch: {name}")
    print(f"fusion_authority_evaluation_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("source_selection_verified=true")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
