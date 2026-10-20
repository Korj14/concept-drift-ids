from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "stage9_5_causal_mutation_assurance_v1.json"
)
TEST_PATH = PROJECT_ROOT / "tests" / "stage9_5" / "test_causal_properties.py"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _run_pytest(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _expected_nodeids(contract: dict[str, Any]) -> list[str]:
    nodeids: list[str] = []
    for item in contract["property_tests"]:
        fixture = str(item["dedicated_fixture"])
        path, test_name = fixture.split("::", 1)
        nodeids.append(f"{path}::{test_name}")
    return sorted(nodeids)


def run(output_dir: Path) -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    expected = _expected_nodeids(contract)

    collect = _run_pytest(
        [
            "tests/stage9_5/test_causal_properties.py",
            "--collect-only",
            "-q",
        ]
    )
    collected = sorted(
        line.strip()
        for line in collect.stdout.splitlines()
        if line.strip().startswith(
            "tests/stage9_5/test_causal_properties.py::"
        )
    )
    missing = sorted(set(expected) - set(collected))
    extra = sorted(set(collected) - set(expected))

    execution = _run_pytest(
        [
            "tests/stage9_5/test_causal_properties.py",
            "-q",
            "--disable-warnings",
        ]
    )

    report: dict[str, Any] = {
        "audit_id": "stage9.5-3-causal-information-properties-v1",
        "contract": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "test_file": str(TEST_PATH.relative_to(PROJECT_ROOT)),
        "required_property_count": int(
            contract["property_closure_rule"]["required_properties"]
        ),
        "expected_nodeids": expected,
        "collected_nodeids": collected,
        "missing_nodeids": missing,
        "extra_nodeids": extra,
        "collect_returncode": int(collect.returncode),
        "pytest_returncode": int(execution.returncode),
        "all_required_fixtures_collected": (
            collect.returncode == 0 and not missing and not extra
        ),
        "all_properties_fail_closed": execution.returncode == 0,
        "scientific_source_modified_for_test_convenience": False,
        "stage10_outcomes_accessed": False,
    }
    report["pass"] = bool(
        report["all_required_fixtures_collected"]
        and report["all_properties_fail_closed"]
        and len(expected)
        == int(contract["property_closure_rule"]["required_fail_closed"])
    )
    report["status"] = "pass" if report["pass"] else "blocked"
    if not report["pass"]:
        report["failure_output"] = {
            "collect_stdout": collect.stdout[-12000:],
            "collect_stderr": collect.stderr[-12000:],
            "pytest_stdout": execution.stdout[-20000:],
            "pytest_stderr": execution.stderr[-20000:],
        }
    report["canonical_sha256"] = _canonical_sha256(
        {k: v for k, v in report.items() if k != "canonical_sha256"}
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "property_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage 9.5-3 Causal / Information Property Assurance",
        "",
        f"- status: **{report['status'].upper()}**",
        f"- required fixtures: **{len(expected)}**",
        f"- collected fixtures: **{len(collected)}**",
        f"- missing fixtures: **{len(missing)}**",
        f"- extra fixtures: **{len(extra)}**",
        f"- pytest return code: **{execution.returncode}**",
        f"- report canonical SHA-256: `{report['canonical_sha256']}`",
    ]
    (output_dir / "PROPERTY_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not report["pass"]:
        raise SystemExit(
            "Stage 9.5-3 blocked: dedicated causal/information property "
            "assurance did not pass exactly."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Stage 9.5-3 causal/information property assurance"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_v1/causal_properties"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
