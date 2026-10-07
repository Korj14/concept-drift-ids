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
    _rule_from_dict,
    _safe_window_metrics,
    _write_csv_new,
    _write_json_new,
)
from concept_drift_ids.system_b_selection_robustness import (
    MANIFEST_PATH as SELECTION_MANIFEST_PATH,
    verify_selection_robustness,
)
from concept_drift_ids.system_b_v2_evaluation import (
    V2_EVIDENCE_METRICS,
    _symbolic_summary,
)


EVALUATION_ID = "system_b_selection_robustness_v1_evaluation"
OUTPUT_DIR = PROJECT_ROOT / "results" / "robustness" / EVALUATION_ID
MANIFEST_PATH = OUTPUT_DIR / "evaluation_manifest.json"
ROWS_PATH = OUTPUT_DIR / "metrics_by_seed_variant.csv"
AGGREGATE_PATH = OUTPUT_DIR / "aggregate_metrics.csv"
SUMMARY_PATH = OUTPUT_DIR / "evaluation_summary.json"


def _load_evaluation_partitions():
    return load_partition("pre_drift"), load_partition("post_drift")


def _load_selection_manifest() -> dict[str, Any]:
    verify_selection_robustness()
    return json.loads(SELECTION_MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_variant_rules(
    selection_manifest: dict[str, Any],
    variant_id: str,
    seed: int,
):
    entry = selection_manifest["variant_inventory"][variant_id]["seeds"][str(seed)]
    payload = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
    return payload, [_rule_from_dict(item) for item in payload["rules"]]


def _aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    groups = sorted(
        {
            (
                str(row["variant_id"]),
                str(row["family"]),
                str(row["partition"]),
            )
            for row in rows
        }
    )
    for variant_id, family, partition in groups:
        selected = [
            row for row in rows
            if row["variant_id"] == variant_id
            and row["partition"] == partition
        ]
        for metric in V2_EVIDENCE_METRICS:
            values = [
                float(row[metric])
                for row in selected
                if row.get(metric) is not None
            ]
            if not values:
                out.append({
                    "variant_id": variant_id,
                    "family": family,
                    "partition": partition,
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
                "variant_id": variant_id,
                "family": family,
                "partition": partition,
                "metric": metric,
                "n_seeds": len(values),
                **summary,
            })
    return out


def evaluate_selection_robustness(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("System-B robustness evaluation is frozen to CPU.")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Robustness evaluation already exists: {OUTPUT_DIR}")
    git = _git_state(require_clean=True)
    selection = _load_selection_manifest()
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    pre, post = _load_evaluation_partitions()
    partitions = {"pre_drift": pre, "post_drift": post}
    device = torch.device("cpu")

    rows: list[dict[str, object]] = []
    for partition_name, partition in partitions.items():
        X = transform_frame(partition.X, preprocessing, dtype=np.dtype("float32"))
        y = partition.y.to_numpy(dtype=np.int8, copy=True)
        for seed in SYSTEM_B_CONFIG["seeds"]:
            record = next(
                item for item in frozen_a["seed_records"] if int(item["seed"]) == seed
            )
            model = _load_checkpoint_model(
                record,
                device=device,
                preprocessing_hash=preprocessing.state_hash,
            )
            neural_prob = predict_probabilities(
                model,
                X,
                device=device,
                batch_size=SYSTEM_A_CONFIG["batch_size"],
            )
            neural_decision = (
                neural_prob >= float(record["threshold"])
            ).astype(np.int8)

            for variant_id, variant_entry in selection["variant_inventory"].items():
                payload, rules = _load_variant_rules(selection, variant_id, seed)
                symbolic = infer_symbolic(
                    X,
                    feature_names=preprocessing.feature_columns,
                    rules=rules,
                )
                weight = float(variant_entry["selected_neural_weight"])
                threshold = float(
                    variant_entry["per_seed_thresholds"][str(seed)]
                )
                fused = fuse_scores(
                    neural_prob,
                    symbolic,
                    neural_weight=weight,
                )
                metrics = _safe_window_metrics(y, fused, threshold)
                rows.append({
                    "variant_id": variant_id,
                    "family": variant_entry["family"],
                    "partition": partition_name,
                    "seed": seed,
                    "sample_count": len(y),
                    "threshold": threshold,
                    "neural_weight": weight,
                    "active_rule_count": len(rules),
                    **_confusion(y, fused, threshold),
                    **metrics,
                    **_symbolic_summary(symbolic, neural_decision, y),
                })
            del model, neural_prob, neural_decision

    aggregate = _aggregate(rows)
    summary = {
        "evaluation_format_version": 1,
        "evaluation_id": EVALUATION_ID,
        "evidence_status": "posthoc_robustness_not_model_selection",
        "selection_manifest_sha256": selection["manifest_sha256"],
        "evaluation_git": git,
        "data_access": {
            "training_used": False,
            "development_used": False,
            "pre_drift_used": True,
            "post_drift_used": True,
        },
        "variant_count": int(selection["variant_count"]),
        "interpretation_firewall": (
            "Held-out robustness results cannot replace accepted R0.v2 or select a "
            "preferred variant. They quantify dependence on prespecified assumptions."
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
    print(f"robustness_evaluation_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"variant_count={selection['variant_count']}")
    print("training_loaded=false")
    print("development_loaded=false")
    print("status=robustness_evaluation_written")


def verify_selection_robustness_evaluation() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing robustness evaluation manifest: {MANIFEST_PATH}")
    selection = _load_selection_manifest()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Robustness evaluation manifest canonical hash mismatch.")
    if manifest.get("selection_manifest_sha256") != selection["manifest_sha256"]:
        raise ValueError("Robustness evaluation references wrong selection freeze.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing robustness evaluation file {name!r}: {path}")
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Robustness evaluation file hash mismatch: {name!r}")
    print(f"robustness_evaluation_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("source_selection_verified=true")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
