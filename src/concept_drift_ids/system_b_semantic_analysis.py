from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from concept_drift_ids.neural import mean_ci95
from concept_drift_ids.scenario_loader import PROJECT_ROOT
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import canonical_json_hash
from concept_drift_ids.system_b import _git_state, _runtime, _write_csv_new, _write_json_new
from concept_drift_ids.system_b_evidence import (
    ACCEPTED_SUPPLEMENT_MANIFEST_SHA256,
    ORIGINAL_EVALUATION_MANIFEST_SHA256,
    SUPPLEMENT_MANIFEST_PATH,
    _verify_original_evaluation,
    verify_system_b_supplement,
)


ANALYSIS_ID = "system_b_v1_semantic_analysis_v1"
ANALYSIS_DIR = PROJECT_ROOT / "results" / "analysis" / ANALYSIS_ID
ANALYSIS_MANIFEST_PATH = ANALYSIS_DIR / "analysis_manifest.json"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _descriptive(values: list[float]) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=np.float64)
    if len(arr) == 0:
        raise ValueError("Cannot summarize an empty vector.")
    q1, q3 = np.quantile(arr, [0.25, 0.75], method="linear")
    return {
        "n": int(len(arr)),
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)) if len(arr) >= 2 else 0.0,
        "median": float(np.median(arr)),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def _exact_class_counts(covered: int, precision: float) -> tuple[int, int]:
    matched_float = float(covered) * float(precision)
    matched = int(round(matched_float))
    if abs(matched_float - matched) > 1e-6:
        raise ValueError(
            "Frozen rule precision does not reconstruct an integer covered-class count."
        )
    return matched, int(covered) - matched


def build_semantic_analysis() -> None:
    if ANALYSIS_DIR.exists():
        raise FileExistsError("Semantic analysis already exists; refusing overwrite.")
    git = _git_state(require_clean=True)
    original = _verify_original_evaluation()
    if original["manifest_sha256"] != ORIGINAL_EVALUATION_MANIFEST_SHA256:
        raise ValueError("Unexpected source evaluation identity.")

    detection = _read_csv(
        PROJECT_ROOT / original["files"]["detection_by_seed"]["path"]
    )
    rule_rows = _read_csv(
        PROJECT_ROOT / original["files"]["rule_quality"]["path"]
    )
    det_by_key = {
        (row["partition"], int(row["seed"])): row for row in detection
    }

    semantic_rules: list[dict[str, object]] = []
    for row in rule_rows:
        covered = int(row["covered_count"])
        semantic_rules.append(
            {
                "system_id": row["system_id"],
                "scenario_id": row["scenario_id"],
                "partition": row["partition"],
                "seed": int(row["seed"]),
                "rule_id": row["rule_id"],
                "consequent": int(row["consequent"]),
                "complexity": int(row["complexity"]),
                "active": covered > 0,
                "support": float(row["support"]),
                "covered_count": covered,
                "class_precision": float(row["class_precision"]) if covered else None,
                "neural_fidelity": float(row["neural_fidelity"]) if covered else None,
                "bootstrap_gate_persistence_stability": float(row["stability"]),
                "activation_rate": float(row["activation_rate"]),
            }
        )

    by_rule = {
        (row["partition"], int(row["seed"]), row["rule_id"]): row
        for row in semantic_rules
    }
    identities = sorted(
        {
            (int(row["seed"]), row["rule_id"])
            for row in semantic_rules
            if row["partition"] == "pre_drift"
        }
    )
    transitions: list[dict[str, object]] = []
    for seed, rule_id in identities:
        pre = by_rule[("pre_drift", seed, rule_id)]
        post = by_rule[("post_drift", seed, rule_id)]
        pre_active, post_active = bool(pre["active"]), bool(post["active"])
        item: dict[str, object] = {
            "system_id": pre["system_id"],
            "scenario_id": pre["scenario_id"],
            "seed": seed,
            "rule_id": rule_id,
            "consequent": int(pre["consequent"]),
            "complexity": int(pre["complexity"]),
            "pre_active": pre_active,
            "post_active": post_active,
            "activity_transition": (
                ("active" if pre_active else "inactive")
                + "_to_"
                + ("active" if post_active else "inactive")
            ),
            "pre_support": float(pre["support"]),
            "post_support": float(post["support"]),
            "delta_support": float(post["support"]) - float(pre["support"]),
            "pre_activation_rate": float(pre["activation_rate"]),
            "post_activation_rate": float(post["activation_rate"]),
            "delta_activation_rate": float(post["activation_rate"]) - float(pre["activation_rate"]),
            "pre_stability": float(pre["bootstrap_gate_persistence_stability"]),
            "post_stability": float(post["bootstrap_gate_persistence_stability"]),
            "delta_stability": float(post["bootstrap_gate_persistence_stability"]) - float(pre["bootstrap_gate_persistence_stability"]),
        }
        for metric in ("class_precision", "neural_fidelity"):
            pv, qv = pre[metric], post[metric]
            item[f"pre_{metric}"] = pv
            item[f"post_{metric}"] = qv
            item[f"delta_{metric}"] = (
                float(qv) - float(pv) if pv is not None and qv is not None else None
            )
        transitions.append(item)

    class_rows: list[dict[str, object]] = []
    for partition in ("pre_drift", "post_drift"):
        for seed in range(5):
            drow = det_by_key[(partition, seed)]
            selected = [
                row for row in semantic_rules
                if row["partition"] == partition and int(row["seed"]) == seed
            ]
            totals = {0: int(drow["benign_count"]), 1: int(drow["attack_count"])}
            covered_by_true = {0: 0, 1: 0}
            correct_by_true = {0: 0, 1: 0}
            total_rule_covered = 0
            for rule in selected:
                covered = int(rule["covered_count"])
                total_rule_covered += covered
                if covered == 0:
                    continue
                matched, other = _exact_class_counts(
                    covered, float(rule["class_precision"])
                )
                consequent = int(rule["consequent"])
                covered_by_true[consequent] += matched
                covered_by_true[1 - consequent] += other
                correct_by_true[consequent] += matched

            expected = int(round(float(drow["resolved_coverage"]) * int(drow["sample_count"])))
            if total_rule_covered != expected:
                raise ValueError(
                    "Frozen R0 coverage is not disjoint as required for exact class derivation."
                )

            for true_class, label in ((0, "benign"), (1, "attack")):
                covered = covered_by_true[true_class]
                class_rows.append(
                    {
                        "system_id": drow["system_id"],
                        "scenario_id": drow["scenario_id"],
                        "partition": partition,
                        "seed": seed,
                        "true_class": true_class,
                        "class_label": label,
                        "class_count": totals[true_class],
                        "covered_count": covered,
                        "class_conditional_symbolic_coverage": covered / totals[true_class],
                        "symbolic_ground_truth_correct_count": correct_by_true[true_class],
                        "symbolic_ground_truth_correctness_on_covered": (
                            correct_by_true[true_class] / covered if covered else None
                        ),
                    }
                )

    class_aggregate: list[dict[str, object]] = []
    for partition in ("pre_drift", "post_drift"):
        for true_class, label in ((0, "benign"), (1, "attack")):
            subset = [
                row for row in class_rows
                if row["partition"] == partition and row["true_class"] == true_class
            ]
            for metric in (
                "class_conditional_symbolic_coverage",
                "symbolic_ground_truth_correctness_on_covered",
            ):
                values = [float(row[metric]) for row in subset if row[metric] is not None]
                ci = mean_ci95(values)
                desc = _descriptive(values)
                class_aggregate.append(
                    {
                        "partition": partition,
                        "true_class": true_class,
                        "class_label": label,
                        "metric": metric,
                        **ci,
                        "median": desc["median"],
                        "q1": desc["q1"],
                        "q3": desc["q3"],
                        "iqr": desc["iqr"],
                        "min": desc["min"],
                        "max": desc["max"],
                    }
                )

    verify_system_b_supplement()
    supplement_manifest = json.loads(
        SUPPLEMENT_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    if supplement_manifest.get("manifest_sha256") != ACCEPTED_SUPPLEMENT_MANIFEST_SHA256:
        raise ValueError("Unexpected System-B supplement identity.")
    supplement = PROJECT_ROOT / "results" / "frozen" / "system_b_v1_supplement_v1"
    metrics = _read_csv(supplement / "metrics_by_seed.csv")
    paired = _read_csv(supplement / "paired_deltas_by_seed.csv")

    metric_desc: list[dict[str, object]] = []
    for partition in ("pre_drift", "post_drift"):
        for metric in sorted({r["metric"] for r in metrics if r["partition"] == partition}):
            values = [
                float(r["value"]) for r in metrics
                if r["partition"] == partition and r["metric"] == metric
            ]
            metric_desc.append({"partition": partition, "metric": metric, **_descriptive(values)})

    paired_desc: list[dict[str, object]] = []
    for metric in sorted({r["metric"] for r in paired}):
        values = [float(r["delta"]) for r in paired if r["metric"] == metric]
        eps = 1e-15
        paired_desc.append(
            {
                "from_partition": "pre_drift",
                "to_partition": "post_drift",
                "metric": metric,
                **_descriptive(values),
                "n_positive": sum(v > eps for v in values),
                "n_negative": sum(v < -eps for v in values),
                "n_zero": sum(abs(v) <= eps for v in values),
            }
        )

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=False)
    tables = {
        "rule_semantics": semantic_rules,
        "rule_semantic_transitions": transitions,
        "class_conditional_symbolic": class_rows,
        "class_conditional_aggregate": class_aggregate,
        "metric_descriptives": metric_desc,
        "paired_delta_descriptives": paired_desc,
    }
    paths: dict[str, Path] = {}
    for name, rows in tables.items():
        path = ANALYSIS_DIR / f"{name}.csv"
        _write_csv_new(path, rows)
        paths[name] = path

    summary = {
        "analysis_format_version": 1,
        "analysis_id": ANALYSIS_ID,
        "source_evaluation_manifest_sha256": original["manifest_sha256"],
        "derivation_git": git,
        "runtime": _runtime(),
        "derivation_contract": {
            "source_frozen_evidence_only": True,
            "raw_partitions_loaded": False,
            "model_checkpoints_loaded": False,
            "r0_modified": False,
            "primary_metrics_modified": False,
        },
        "rows": {name: len(rows) for name, rows in tables.items()},
        "note": (
            "Inactive-rule precision/fidelity are undefined (null). Class-conditional "
            "coverage/correctness are exactly derivable because frozen R0 leaves are disjoint."
        ),
    }
    summary_path = ANALYSIS_DIR / "analysis_summary.json"
    _write_json_new(summary_path, summary)
    paths["summary"] = summary_path

    manifest = {
        "manifest_format_version": 1,
        "analysis_id": ANALYSIS_ID,
        "source_evaluation_manifest_sha256": original["manifest_sha256"],
        "derivation_git": git,
        "files": {
            name: {"path": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(ANALYSIS_MANIFEST_PATH, manifest)
    print(f"analysis_manifest={ANALYSIS_MANIFEST_PATH}")
    print(f"analysis_manifest_hash={manifest['manifest_sha256']}")
    print("source_frozen_evidence_only=true")
    print("raw_partitions_loaded=false")
    print("model_checkpoints_loaded=false")
    print("status=system_b_semantic_analysis_written")


def verify_semantic_analysis() -> None:
    original = _verify_original_evaluation()
    manifest = json.loads(ANALYSIS_MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Semantic-analysis manifest hash mismatch.")
    if manifest["source_evaluation_manifest_sha256"] != original["manifest_sha256"]:
        raise ValueError("Semantic analysis references the wrong evaluation.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Semantic-analysis artifact mismatch for {name!r}.")
    print(f"analysis_manifest={ANALYSIS_MANIFEST_PATH}")
    print(f"analysis_manifest_hash={stored}")
    print("source_frozen_evidence_only=true")
    print("raw_partitions_loaded=false")
    print("model_checkpoints_loaded=false")
    print("status=verified")
