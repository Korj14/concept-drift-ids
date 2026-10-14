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
TEST_PATH = PROJECT_ROOT / "tests" / "stage9_5" / "test_targeted_mutations.py"


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


def _pytest(nodeid: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            nodeid,
            "-q",
            "--disable-warnings",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run(output_dir: Path) -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    results: list[dict[str, Any]] = []
    for mutant in contract["mutants"]:
        nodeid = str(mutant["kill_fixture"])
        execution = _pytest(nodeid)
        killed = execution.returncode == 0
        item = {
            "mutant_id": mutant["id"],
            "description": mutant["description"],
            "kill_fixture": nodeid,
            "killed": killed,
            "pytest_returncode": int(execution.returncode),
        }
        if not killed:
            item["stdout"] = execution.stdout[-12000:]
            item["stderr"] = execution.stderr[-12000:]
        results.append(item)

    required = int(contract["mutation_closure_rule"]["defined_mutants"])
    killed_count = sum(bool(item["killed"]) for item in results)
    report: dict[str, Any] = {
        "audit_id": "stage9.5-4-targeted-mutation-assurance-v1",
        "contract": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "test_file": str(TEST_PATH.relative_to(PROJECT_ROOT)),
        "defined_mutants": required,
        "executed_mutants": len(results),
        "killed_mutants": killed_count,
        "kill_rate": killed_count / required if required else 0.0,
        "required_kill_rate": float(
            contract["mutation_closure_rule"]["required_kill_rate"]
        ),
        "mutants": results,
        "production_source_files_modified": False,
        "mutation_method": (
            "inspect actual production function source; assert exact mutation "
            "substrate occurrence count; compile mutated function in test-only "
            "memory; compare behavior with the unmutated production function"
        ),
        "stage10_outcomes_accessed": False,
    }
    report["pass"] = bool(
        len(results) == required
        and killed_count
        == int(contract["mutation_closure_rule"]["required_killed"])
        and report["kill_rate"]
        == float(contract["mutation_closure_rule"]["required_kill_rate"])
    )
    report["status"] = "pass" if report["pass"] else "blocked"
    report["canonical_sha256"] = _canonical_sha256(
        {k: v for k, v in report.items() if k != "canonical_sha256"}
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "mutation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage 9.5-4 Targeted Mutation Assurance",
        "",
        f"- status: **{report['status'].upper()}**",
        f"- defined mutants: **{required}**",
        f"- killed mutants: **{killed_count}**",
        f"- kill rate: **{report['kill_rate']:.3f}**",
        f"- report canonical SHA-256: `{report['canonical_sha256']}`",
        "",
        "## Mutants",
        "",
    ]
    lines += [
        f"- {item['mutant_id']}: {'KILLED' if item['killed'] else 'SURVIVED'}"
        for item in results
    ]
    (output_dir / "MUTATION_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    if not report["pass"]:
        survivors = [
            item["mutant_id"] for item in results if not item["killed"]
        ]
        raise SystemExit(
            f"Stage 9.5-4 blocked: killed {killed_count}/{required}; "
            f"survivors={survivors}"
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Stage 9.5-4 targeted mutation assurance"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_v1/targeted_mutations"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
