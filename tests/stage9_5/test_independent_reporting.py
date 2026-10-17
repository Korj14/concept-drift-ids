from __future__ import annotations

import ast
import json
from pathlib import Path

from tools.stage9_5.independent_reporting import PROJECT_ROOT, run

PROHIBITED = {
    "concept_drift_ids.cd_analysis",
    "concept_drift_ids.cd_primary_export",
    "concept_drift_ids.cd_stage9_export",
}


def test_reporting_tool_does_not_import_production_reporting_modules() -> None:
    path = PROJECT_ROOT / "tools/stage9_5/independent_reporting.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    assert not any(
        name == blocked or name.startswith(blocked + ".")
        for name in imports
        for blocked in PROHIBITED
    )


def test_independent_reporting_integration(tmp_path: Path) -> None:
    report = run(tmp_path)
    assert report["pass"] is True
    assert report["mismatch_count"] == 0
    assert report["missing_outputs"] == []
    assert report["oracle_comparison_count"] > 0

    contract = json.loads(
        (
            PROJECT_ROOT
            / "data/manifests/stage9_5_claim_reporting_v1.json"
        ).read_text(encoding="utf-8")
    )
    for relative in contract["stage9_5_8"]["required_outputs"]:
        assert (tmp_path / relative).is_file()


def test_emitted_records_carry_claim_and_selector(tmp_path: Path) -> None:
    run(tmp_path)
    for path in list((tmp_path / "tables").glob("*.json")) + list(
        (tmp_path / "figures").glob("*.json")
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["rounding_applied"] is False
        for record in payload["records"]:
            assert record["claim_id"]
            assert record["evidence_selector"]
            assert "value" in record
