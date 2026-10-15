from __future__ import annotations

import json
from pathlib import Path

from tools.stage9_5 import static_assurance


CONTRACT = "stage9_5_static_assurance_v1_8.json"


def _contract() -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    return json.loads(
        (root / "data" / "manifests" / CONTRACT).read_text(
            encoding="utf-8"
        )
    )


def test_v1_8_delta_scope_is_exact_and_unique() -> None:
    contract = _contract()
    scope = contract["scope"]
    expected_tools = {
        "tools/stage9_5/claim_traceability.py",
        "tools/stage9_5/independent_reporting.py",
        "tools/stage9_5/static_assurance.py",
    }
    expected_tests = {
        "tests/stage9_5/test_claim_traceability.py",
        "tests/stage9_5/test_independent_reporting.py",
        "tests/stage9_5/test_supplemental_static_assurance.py",
    }
    assert set(scope["assurance_tool_files"]) == expected_tools
    assert set(scope["assurance_test_files"]) == expected_tests
    assert set(scope["mypy_files"]) == expected_tools
    assert set(scope["ruff_files"]) == expected_tools | expected_tests
    assert len(scope["ruff_files"]) == len(set(scope["ruff_files"]))
    assert len(scope["mypy_files"]) == len(set(scope["mypy_files"]))
    assert scope["delta_basis"]["scientific_source_files_changed"] == 0


def test_v1_8_preserves_v1_4_baseline_authority() -> None:
    contract = _contract()
    baseline = contract["accepted_baseline"]
    assert static_assurance.CONTRACT_PATH.name == (
        "stage9_5_static_assurance_v1_4.json"
    )
    assert baseline["closure_commit"] == (
        "6bd3511a395b1e2db39e9370c94b3a099328c9e8"
    )
    assert baseline["scientific_fingerprint_set_sha256"] == (
        "268693732ad427a3e21482634b75b7c0d72bf61d70847340bf14cc45678754df"
    )


def test_v1_8_uses_explicit_package_bases_only_for_delta() -> None:
    contract = _contract()
    assert contract["mypy"]["explicit_package_bases"] is True
    source = Path(static_assurance.__file__).read_text(encoding="utf-8")
    assert '"--explicit-package-bases"' in source
    assert '"--contract"' in source


def test_v1_8_delta_python_scope_compiles() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = _contract()
    paths = sorted(
        set(contract["scope"]["assurance_tool_files"])
        | set(contract["scope"]["assurance_test_files"])
    )
    for relative in paths:
        compile(
            (root / relative).read_text(encoding="utf-8"),
            relative,
            "exec",
        )
