from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from concept_drift_ids.symbolic import canonical_json_hash


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "results" / "frozen" / "system_b_v1"
EVAL_MANIFEST = EVAL_DIR / "evaluation_manifest.json"
SYSTEM_MANIFEST = ROOT / "data" / "manifests" / "system_b_v1.json"

EXPECTED_EVALUATION_HASH = (
    "f44cad2ed9674bcb7118f05f174f845b5dfb135f95e2cb2b4a230f0f998c3e42"
)
EXPECTED_SYSTEM_HASH = (
    "6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8"
)
EXPECTED_EXECUTION_COMMIT = "245ca52371d7cdbcf8475b1d86b4b95d2b9850f5"


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_frozen_system_b_evaluation_contract() -> None:
    manifest = json.loads(EVAL_MANIFEST.read_text(encoding="utf-8"))
    stored = manifest["manifest_sha256"]
    core = dict(manifest)
    core.pop("manifest_sha256")

    assert stored == EXPECTED_EVALUATION_HASH
    assert canonical_json_hash(core) == stored
    assert manifest["system_manifest_sha256"] == EXPECTED_SYSTEM_HASH
    assert manifest["evaluation_git"] == {
        "commit": EXPECTED_EXECUTION_COMMIT,
        "branch": "stage4-system-b",
        "clean": "true",
    }

    system_manifest = json.loads(SYSTEM_MANIFEST.read_text(encoding="utf-8"))
    assert system_manifest["manifest_sha256"] == EXPECTED_SYSTEM_HASH

    for entry in manifest["files"].values():
        path = ROOT / entry["path"]
        assert path.is_file()
        assert _file_hash(path) == entry["sha256"]

    detection = _rows(EVAL_DIR / "detection_by_seed.csv")
    rules = _rows(EVAL_DIR / "rule_quality_by_seed_partition.csv")
    windows = _rows(EVAL_DIR / "window_metrics.csv")

    assert len(detection) == 10
    assert len(rules) == 72
    assert len(windows) == 140
    assert {int(row["seed"]) for row in detection} == {0, 1, 2, 3, 4}
    assert {row["partition"] for row in detection} == {"pre_drift", "post_drift"}

    for row in detection:
        n = int(row["sample_count"])
        tn, fp = int(row["tn"]), int(row["fp"])
        fn, tp = int(row["fn"]), int(row["tp"])
        assert tn + fp + fn + tp == n
        assert tn + fp == int(row["benign_count"])
        assert fn + tp == int(row["attack_count"])
        assert int(row["benign_count"]) + int(row["attack_count"]) == n

    expected_rule_counts = {0: 7, 1: 8, 2: 7, 3: 8, 4: 6}
    for seed, count in expected_rule_counts.items():
        pre = sorted(
            row["rule_id"]
            for row in rules
            if int(row["seed"]) == seed and row["partition"] == "pre_drift"
        )
        post = sorted(
            row["rule_id"]
            for row in rules
            if int(row["seed"]) == seed and row["partition"] == "post_drift"
        )
        assert len(pre) == count
        assert pre == post

    for seed in range(5):
        for partition, expected_total in (
            ("pre_drift", 69_260),
            ("post_drift", 69_270),
        ):
            selected = [
                row
                for row in windows
                if int(row["seed"]) == seed and row["partition"] == partition
            ]
            assert len(selected) == 14
            assert sum(int(row["sample_count"]) for row in selected) == expected_total
            assert int(selected[0]["row_start"]) == 0
            assert int(selected[-1]["row_end"]) == expected_total

    assert min(float(row["resolved_coverage"]) for row in windows) > 0.0
