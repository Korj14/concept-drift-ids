from __future__ import annotations

import json
from pathlib import Path

from tools.stage9_5.parameter_scan import _canonical_sha256, _registered_ids, run


def _minimal_repo(tmp_path: Path) -> None:
    (tmp_path / "data/manifests").mkdir(parents=True)
    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    (tmp_path / "STAGE8_PRIMARY_EXECUTION_PROTOCOL.md").write_text(
        "threshold 0.5\n", encoding="utf-8"
    )
    (tmp_path / "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md").write_text(
        "latency 5000\n", encoding="utf-8"
    )
    (tmp_path / "Q1_ADVERSARIAL_AUDIT_REGISTER.md").write_text(
        "boundary 69260\n", encoding="utf-8"
    )
    (tmp_path / "METHODOLOGY_LEDGER.md").write_text(
        "five seeds 0 1 2 3 4\n", encoding="utf-8"
    )
    (tmp_path / "STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md").write_text(
        "lambda 1\n", encoding="utf-8"
    )


def test_registered_value_matching_is_source_scoped() -> None:
    register = {
        "entries": [
            {
                "id": "x",
                "source_locations": ["a.py"],
                "accepted_value": {"threshold": 0.5},
            }
        ]
    }
    assert _registered_ids(register, "a.py", "threshold", 0.5) == ("x",)
    assert _registered_ids(register, "b.py", "threshold", 0.5) == ()


def test_canonical_hash_is_order_independent_for_mapping() -> None:
    assert _canonical_sha256({"a": 1, "b": 2}) == _canonical_sha256({"b": 2, "a": 1})


def test_scan_blocks_unregistered_high_leverage_constant(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    source = tmp_path / "src/concept_drift_ids/example.py"
    source.write_text("LABEL_LATENCY = 5000\n", encoding="utf-8")
    for name in ["a.json", "b.json", "c.json", "d.json"]:
        (tmp_path / "data/manifests" / name).write_text("{}\n", encoding="utf-8")

    register = {
        "protocol_id": "stage9.5-q1-assurance-v1",
        "upstream_closure_head": "head",
        "entries": [],
        "scan_roots": {
            "scientific_source": ["src/concept_drift_ids/example.py"],
            "manifests": [f"data/manifests/{x}" for x in ["a.json","b.json","c.json","d.json"]],
            "protocols": [
                "STAGE8_PRIMARY_EXECUTION_PROTOCOL.md",
                "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md",
                "Q1_ADVERSARIAL_AUDIT_REGISTER.md",
                "METHODOLOGY_LEDGER.md",
                "STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md",
            ],
        },
    }
    path = tmp_path / "data/manifests/stage9_5_parameter_register_v1_1.json"
    path.write_text(json.dumps(register), encoding="utf-8")

    try:
        run(tmp_path, tmp_path / "out", fail_on_unclassified_high=True)
    except SystemExit as exc:
        assert "blocked" in str(exc).lower()
    else:
        raise AssertionError("expected fail-closed scan")


def test_scan_passes_when_high_leverage_constant_is_registered(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    source = tmp_path / "src/concept_drift_ids/example.py"
    source.write_text("LABEL_LATENCY = 5000\n", encoding="utf-8")
    for name in ["a.json", "b.json", "c.json", "d.json"]:
        (tmp_path / "data/manifests" / name).write_text("{}\n", encoding="utf-8")

    register = {
        "protocol_id": "stage9.5-q1-assurance-v1",
        "upstream_closure_head": "head",
        "entries": [
            {
                "id": "timing.label_latency",
                "source_locations": ["src/concept_drift_ids/example.py"],
                "accepted_value": 5000,
            }
        ],
        "scan_roots": {
            "scientific_source": ["src/concept_drift_ids/example.py"],
            "manifests": [f"data/manifests/{x}" for x in ["a.json","b.json","c.json","d.json"]],
            "protocols": [],
        },
    }
    path = tmp_path / "data/manifests/stage9_5_parameter_register_v1_1.json"
    path.write_text(json.dumps(register), encoding="utf-8")

    report = run(tmp_path, tmp_path / "out", fail_on_unclassified_high=True)
    assert report["pass"] is True
    assert report["counts"]["unclassified_high_leverage_candidates"] == 0
