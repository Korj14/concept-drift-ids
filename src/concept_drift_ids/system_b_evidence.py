from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from concept_drift_ids.scenario_loader import PROJECT_ROOT
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import canonical_json_hash
from concept_drift_ids.system_b import (
    ACCEPTED_SYSTEM_B_MANIFEST_SHA256,
    EVALUATION_MANIFEST_PATH,
    SYSTEM_B_CONFIG,
    _build_metric_tables,
    _git_state,
    _rule_staleness_deltas,
    _runtime,
    _write_csv_new,
    _write_json_new,
)


ORIGINAL_EVALUATION_MANIFEST_SHA256 = (
    "f44cad2ed9674bcb7118f05f174f845b5dfb135f95e2cb2b4a230f0f998c3e42"
)
SUPPLEMENT_ID = "system_b_v1_supplement_v1"
ACCEPTED_SUPPLEMENT_MANIFEST_SHA256 = (
    "70d41b210ed54f2fa2269ec738ccd94100148d701bb5a2ae79d8d30839e9d190"
)
SUPPLEMENT_DIR = PROJECT_ROOT / "results" / "frozen" / SUPPLEMENT_ID
SUPPLEMENT_MANIFEST_PATH = SUPPLEMENT_DIR / "supplement_manifest.json"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _verify_original_evaluation() -> dict[str, Any]:
    if not EVALUATION_MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"Missing frozen System-B evaluation manifest: {EVALUATION_MANIFEST_PATH}"
        )
    manifest = json.loads(EVALUATION_MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Original System-B evaluation manifest hash mismatch.")
    if stored != ORIGINAL_EVALUATION_MANIFEST_SHA256:
        raise ValueError(
            "Original System-B evaluation is not the accepted first-run identity."
        )
    if manifest.get("system_manifest_sha256") != ACCEPTED_SYSTEM_B_MANIFEST_SHA256:
        raise ValueError("Original System-B evaluation references the wrong R0 manifest.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing original System-B evaluation artifact {name!r}: {path}"
            )
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(
                f"Original System-B evaluation artifact hash mismatch for {name!r}."
            )
    return manifest


def build_system_b_supplement() -> None:
    if SUPPLEMENT_MANIFEST_PATH.exists() or SUPPLEMENT_DIR.exists():
        raise FileExistsError(
            "System-B evaluation supplement already exists; refusing overwrite."
        )

    git = _git_state(require_clean=True)
    original = _verify_original_evaluation()

    detection_path = PROJECT_ROOT / original["files"]["detection_by_seed"]["path"]
    rule_path = PROJECT_ROOT / original["files"]["rule_quality"]["path"]
    detection_rows = _read_csv(detection_path)
    rule_rows = _read_csv(rule_path)

    (
        metric_rows,
        aggregate_metric_rows,
        paired_delta_rows,
        aggregate_paired_delta_rows,
    ) = _build_metric_tables(
        detection_rows,
        scenario_version=int(original["scenario_version"]),
    )
    staleness_rows = _rule_staleness_deltas(
        rule_rows,
        scenario_version=int(original["scenario_version"]),
    )

    SUPPLEMENT_DIR.mkdir(parents=True, exist_ok=False)
    metric_path = SUPPLEMENT_DIR / "metrics_by_seed.csv"
    aggregate_metric_path = SUPPLEMENT_DIR / "aggregate_metrics.csv"
    paired_delta_path = SUPPLEMENT_DIR / "paired_deltas_by_seed.csv"
    aggregate_paired_delta_path = SUPPLEMENT_DIR / "aggregate_paired_deltas.csv"
    staleness_path = SUPPLEMENT_DIR / "rule_staleness_deltas.csv"

    _write_csv_new(metric_path, metric_rows)
    _write_csv_new(aggregate_metric_path, aggregate_metric_rows)
    _write_csv_new(paired_delta_path, paired_delta_rows)
    _write_csv_new(aggregate_paired_delta_path, aggregate_paired_delta_rows)
    _write_csv_new(staleness_path, staleness_rows)

    summary = {
        "format_version": 1,
        "supplement_id": SUPPLEMENT_ID,
        "source_evaluation_manifest_sha256": original["manifest_sha256"],
        "source_system_manifest_sha256": original["system_manifest_sha256"],
        "scenario_id": original["scenario_id"],
        "scenario_version": original["scenario_version"],
        "derivation_git": git,
        "runtime": _runtime(),
        "derivation_contract": {
            "source_frozen_evidence_only": True,
            "raw_training_loaded": False,
            "raw_development_loaded": False,
            "raw_pre_drift_loaded": False,
            "raw_post_drift_loaded": False,
            "model_checkpoint_loaded": False,
            "r0_modified": False,
            "thresholds_modified": False,
            "fusion_weight_modified": False,
        },
        "rows": {
            "metrics_by_seed": len(metric_rows),
            "aggregate_metrics": len(aggregate_metric_rows),
            "paired_deltas_by_seed": len(paired_delta_rows),
            "aggregate_paired_deltas": len(aggregate_paired_delta_rows),
            "rule_staleness_deltas": len(staleness_rows),
        },
        "note": (
            "Additive derivation from the immutable first System-B evaluation. "
            "No model or held-out partition was rerun."
        ),
    }
    summary_path = SUPPLEMENT_DIR / "supplement_summary.json"
    _write_json_new(summary_path, summary)

    files = {
        "summary": summary_path,
        "metrics_by_seed": metric_path,
        "aggregate_metrics": aggregate_metric_path,
        "paired_deltas_by_seed": paired_delta_path,
        "aggregate_paired_deltas": aggregate_paired_delta_path,
        "rule_staleness_deltas": staleness_path,
    }
    supplement_manifest = {
        "manifest_format_version": 1,
        "supplement_id": SUPPLEMENT_ID,
        "source_evaluation_manifest_sha256": original["manifest_sha256"],
        "source_system_manifest_sha256": original["system_manifest_sha256"],
        "scenario_id": original["scenario_id"],
        "scenario_version": original["scenario_version"],
        "derivation_git": git,
        "files": {
            name: {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
            for name, path in files.items()
        },
    }
    supplement_manifest["manifest_sha256"] = canonical_json_hash(supplement_manifest)
    _write_json_new(SUPPLEMENT_MANIFEST_PATH, supplement_manifest)

    print(f"supplement_manifest={SUPPLEMENT_MANIFEST_PATH}")
    print(f"supplement_manifest_hash={supplement_manifest['manifest_sha256']}")
    print("source_frozen_evidence_only=true")
    print("held_out_model_rerun=false")
    print("status=system_b_supplement_written")


def verify_system_b_supplement() -> None:
    original = _verify_original_evaluation()
    if not SUPPLEMENT_MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"Missing System-B supplement manifest: {SUPPLEMENT_MANIFEST_PATH}"
        )
    manifest = json.loads(SUPPLEMENT_MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("System-B supplement manifest hash mismatch.")
    if stored != ACCEPTED_SUPPLEMENT_MANIFEST_SHA256:
        raise ValueError("System-B supplement is not the accepted frozen identity.")
    if manifest.get("source_evaluation_manifest_sha256") != original["manifest_sha256"]:
        raise ValueError("System-B supplement references the wrong original evaluation.")
    if manifest.get("source_system_manifest_sha256") != ACCEPTED_SYSTEM_B_MANIFEST_SHA256:
        raise ValueError("System-B supplement references the wrong R0 manifest.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing System-B supplement artifact {name!r}: {path}")
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"System-B supplement artifact hash mismatch for {name!r}.")
    print(f"supplement_manifest={SUPPLEMENT_MANIFEST_PATH}")
    print(f"supplement_manifest_hash={stored}")
    print("source_frozen_evidence_only=true")
    print("held_out_model_rerun=false")
    print("status=verified")
