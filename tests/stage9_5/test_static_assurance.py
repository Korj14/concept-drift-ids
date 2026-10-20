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
            / "stage9_5_static_assurance_v1_4.json"
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
            / "stage9_5_static_assurance_v1_4.json"
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
            / "stage9_5_static_assurance_v1_4.json"
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
            / "stage9_5_static_assurance_v1_4.json"
        ).read_text(encoding="utf-8")
    )
    paths = sorted(
        set(contract["scope"]["assurance_tool_files"])
        | set(contract["scope"]["assurance_test_files"])
    )
    for relative in paths:
        source = (root / relative).read_text(encoding="utf-8")
        compile(source, relative, "exec")
