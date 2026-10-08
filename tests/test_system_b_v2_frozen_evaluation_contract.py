from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from concept_drift_ids.symbolic import canonical_json_hash
from concept_drift_ids.system_b_r0_v2 import ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "results" / "frozen" / "system_b_v2_corrected_v1"
EVAL_MANIFEST = EVAL_DIR / "evaluation_manifest.json"

EXPECTED_EVALUATION_MANIFEST_SHA256 = (
    "583fa356c291bd7b2b275d726bb9eee31ae9aa5470cca50f0146c91642873710"
)
EXPECTED_EXECUTION_COMMIT = "51690ea23906ab87b9406311eacf381c7a22b5fb"
EXPECTED_FILES = {
    "detection_by_seed": "6ce19d1cac57a671c850bd5987cb794910e85567d6568f4017f4f1285ed2dda7",
    "metrics_by_seed": "42c8b8a446f3d0d306dabadc0e60e0065d0eb270a06e45cbf778361d80b29770",
    "aggregate_metrics": "96577eff95b73d43aeb97f4da89459123cdf198318cbe5ad6385176b829373c1",
    "paired_deltas_by_seed": "895da3f9ac416290964ea8ee9311be991612e678c34e6157f596d554057db35d",
    "aggregate_paired_deltas": "3aa6683d401048369093644f2b5e907562df1938f532d2949271c64f9b15586d",
    "rule_quality": "cf5f287295edab678655849bd261897ceaeb002593d52955104aed5d20c4dc41",
    "rule_staleness_deltas": "74300f741d3cb6d01f95b0eaad3623fae01ad4ec69f6b1a2b6d0aba45988bc8e",
    "window_metrics": "e09f38c5cb3813051e753fa6c70679eee70b21b61f50be664d6e91f66f499f10",
    "runtime": "6a8b3e283aa6402651db4458bf27dd7cb1506a13acfbe48568db540f04ea00c2",
    "summary": "4215f87259798fe017419d203f05d7c4d14e7f623b27c3747b48be95021d8a55",
}


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_frozen_corrected_system_b_v2_evaluation_contract() -> None:
    manifest = json.loads(EVAL_MANIFEST.read_text(encoding="utf-8"))
    stored = manifest["manifest_sha256"]
    core = dict(manifest)
    core.pop("manifest_sha256")

    assert stored == EXPECTED_EVALUATION_MANIFEST_SHA256
    assert canonical_json_hash(core) == stored
    assert manifest["system_manifest_sha256"] == ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256
    assert manifest["evidence_status"] == (
        "implementation_defect_correction_not_first_look"
    )
    assert manifest["evaluation_git"] == {
        "commit": EXPECTED_EXECUTION_COMMIT,
        "branch": "stage4-system-b",
        "clean": "true",
    }
    assert manifest["runtime"]["python"] == "3.11.9"

    for name, expected_hash in EXPECTED_FILES.items():
        entry = manifest["files"][name]
        path = ROOT / entry["path"]
        assert path.is_file()
        assert entry["sha256"] == expected_hash
        assert _file_hash(path) == expected_hash

    detection = _rows(EVAL_DIR / "detection_by_seed.csv")
    rules = _rows(EVAL_DIR / "rule_quality_by_seed_partition.csv")
    staleness = _rows(EVAL_DIR / "rule_staleness_deltas.csv")
    windows = _rows(EVAL_DIR / "window_metrics.csv")
    runtime = _rows(EVAL_DIR / "runtime_by_seed_partition.csv")

    assert len(detection) == 10
    assert len(rules) == 64
    assert len(staleness) == 32
    assert len(windows) == 140
    assert len(runtime) == 10
    assert {int(row["seed"]) for row in detection} == {0, 1, 2, 3, 4}
    assert {row["partition"] for row in detection} == {"pre_drift", "post_drift"}

    for row in detection:
        n = int(row["sample_count"])
        benign = int(row["benign_count"])
        attack = int(row["attack_count"])
        tn, fp = int(row["tn"]), int(row["fp"])
        fn, tp = int(row["fn"]), int(row["tp"])
        assert tn + fp + fn + tp == n
        assert tn + fp == benign
        assert fn + tp == attack
        assert benign + attack == n
        assert float(row["conflict_abstention_rate"]) == 0.0

    expected_rule_counts = {0: 7, 1: 6, 2: 7, 3: 6, 4: 6}
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

    assert all(
        int(row["imputed_antecedent_activation_count"]) == 0
        for row in rules
    )

    transitions: dict[str, int] = {}
    for row in staleness:
        transitions[row["gate_transition"]] = transitions.get(
            row["gate_transition"], 0
        ) + 1
    assert transitions == {
        "pass_to_pass": 18,
        "fail_to_pass": 7,
        "fail_to_fail": 6,
        "pass_to_fail": 1,
    }

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

    assert all(
        int(row["symbolic_fusion_warmup_repeats"]) == 1
        and int(row["symbolic_fusion_measured_repeats"]) == 5
        for row in runtime
    )
