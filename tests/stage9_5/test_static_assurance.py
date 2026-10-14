from __future__ import annotations

import json
from pathlib import Path

from tools.stage9_5.static_assurance import _parse_mypy_findings


def test_static_assurance_contract_has_unique_frozen_scope() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            root
            / "data"
            / "manifests"
            / "stage9_5_static_assurance_v1_7.json"
        ).read_text(encoding="utf-8")
    )
    ruff_files = contract["scope"]["ruff_files"]
    mypy_files = contract["scope"]["mypy_files"]
    assert len(ruff_files) == len(set(ruff_files))
    assert len(mypy_files) == len(set(mypy_files))
    assert len(contract["scope"]["scientific_files"]) == 38
    assert set(mypy_files).issubset(set(ruff_files))
    assert all((root / path).is_file() for path in ruff_files)


def test_historical_lock_is_not_a_developer_tool_target() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            root
            / "data"
            / "manifests"
            / "stage9_5_static_assurance_v1_7.json"
        ).read_text(encoding="utf-8")
    )
    specs = {
        contract["developer_tools"]["ruff"]["install_spec"],
        contract["developer_tools"]["mypy"]["install_spec"],
    }
    assert specs == {"ruff==0.17.0", "mypy==2.4.0"}
    assert contract["historical_runtime_lock"]["must_not_be_modified"] is True


def test_mypy_finding_parser_handles_line_and_column() -> None:
    findings = _parse_mypy_findings(
        "src/example.py:12:7: error: Incompatible types [assignment]\n"
        "src/other.py:9: error: Missing annotation [var-annotated]\n"
    )
    assert findings == [
        {
            "path": "src/example.py",
            "line": 12,
            "column": 7,
            "message": "Incompatible types [assignment]",
        },
        {
            "path": "src/other.py",
            "line": 9,
            "column": None,
            "message": "Missing annotation [var-annotated]",
        },
    ]


def test_static_assurance_scope_includes_itself() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            root
            / "data"
            / "manifests"
            / "stage9_5_static_assurance_v1_7.json"
        ).read_text(encoding="utf-8")
    )
    assert "tools/stage9_5/static_assurance.py" in contract["scope"]["ruff_files"]
    assert "tools/stage9_5/static_assurance.py" in contract["scope"]["mypy_files"]
    assert "tests/stage9_5/test_static_assurance.py" in contract["scope"]["ruff_files"]


def test_stage9_5_assurance_python_scope_compiles() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            root
            / "data"
            / "manifests"
            / "stage9_5_static_assurance_v1_7.json"
        ).read_text(encoding="utf-8")
    )
    paths = sorted(
        set(contract["scope"]["assurance_tool_files"])
        | set(contract["scope"]["assurance_test_files"])
    )
    for relative in paths:
        source = (root / relative).read_text(encoding="utf-8")
        compile(source, relative, "exec")


def test_stage9_5_7_8_assurance_files_are_static_scoped() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            root
            / "data"
            / "manifests"
            / "stage9_5_static_assurance_v1_7.json"
        ).read_text(encoding="utf-8")
    )
    for relative in (
        "tools/stage9_5/claim_traceability.py",
        "tools/stage9_5/independent_reporting.py",
    ):
        assert relative in contract["scope"]["ruff_files"]
        assert relative in contract["scope"]["mypy_files"]
    for relative in (
        "tests/stage9_5/test_claim_traceability.py",
        "tests/stage9_5/test_independent_reporting.py",
    ):
        assert relative in contract["scope"]["ruff_files"]


def test_mypy_uses_explicit_package_bases() -> None:
    from tools.stage9_5 import static_assurance

    source = Path(static_assurance.__file__).read_text(encoding="utf-8")
    assert '"--explicit-package-bases"' in source


def test_v1_7_scope_is_post_v1_4_delta_only() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            root
            / "data"
            / "manifests"
            / "stage9_5_static_assurance_v1_7.json"
        ).read_text(encoding="utf-8")
    )
    expected_tools = {
        "tools/stage9_5/claim_traceability.py",
        "tools/stage9_5/independent_reporting.py",
        "tools/stage9_5/static_assurance.py",
    }
    expected_tests = {
        "tests/stage9_5/test_claim_traceability.py",
        "tests/stage9_5/test_independent_reporting.py",
        "tests/stage9_5/test_static_assurance.py",
    }
    assert set(contract["scope"]["assurance_tool_files"]) == expected_tools
    assert set(contract["scope"]["assurance_test_files"]) == expected_tests
    assert set(contract["scope"]["mypy_files"]) == expected_tools
    assert set(contract["scope"]["ruff_files"]) == expected_tools | expected_tests
    assert contract["scope"]["delta_basis"]["scientific_source_files_changed"] == 0
