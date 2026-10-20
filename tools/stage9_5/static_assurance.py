from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_static_assurance_v1_4.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _tool_version(executable: str, expected: str) -> dict[str, Any]:
    result = _run([executable, "--version"])
    observed = (result.stdout or result.stderr).strip()
    return {
        "expected": expected,
        "observed": observed,
        "returncode": result.returncode,
        "matches": result.returncode == 0 and expected in observed,
    }


def _parse_mypy_findings(stdout: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if ": error:" not in line:
            continue
        prefix, message = line.split(": error:", 1)
        parts = prefix.rsplit(":", 2)
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            path, line_no, column = parts
            findings.append(
                {
                    "path": path.replace("\\", "/"),
                    "line": int(line_no),
                    "column": int(column),
                    "message": message.strip(),
                }
            )
        elif len(parts) == 2 and parts[1].isdigit():
            path, line_no = parts
            findings.append(
                {
                    "path": path.replace("\\", "/"),
                    "line": int(line_no),
                    "column": None,
                    "message": message.strip(),
                }
            )
        else:
            findings.append(
                {
                    "path": prefix.replace("\\", "/"),
                    "line": None,
                    "column": None,
                    "message": message.strip(),
                }
            )
    return findings


def run(
    output_dir: Path,
    *,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    if not contract_path.is_absolute():
        contract_path = PROJECT_ROOT / contract_path
    contract = _load_json(contract_path)
    lock = PROJECT_ROOT / contract["historical_runtime_lock"]["path"]
    lock_sha = _sha256_file(lock)

    ruff_files = [str(item) for item in contract["scope"]["ruff_files"]]
    mypy_files = [str(item) for item in contract["scope"]["mypy_files"]]

    missing_files = sorted(
        path
        for path in set(ruff_files + mypy_files)
        if not (PROJECT_ROOT / path).is_file()
    )

    ruff_version = _tool_version(
        "ruff",
        str(contract["developer_tools"]["ruff"]["version"]),
    )
    mypy_version = _tool_version(
        "mypy",
        str(contract["developer_tools"]["mypy"]["version"]),
    )

    ruff = _run(
        [
            "ruff",
            "check",
            "--output-format",
            "json",
            *ruff_files,
        ]
    )
    ruff_findings: list[dict[str, Any]] = []
    ruff_parse_error: str | None = None
    if ruff.stdout.strip():
        try:
            parsed_ruff = json.loads(ruff.stdout)
        except json.JSONDecodeError as exc:
            ruff_parse_error = f"JSONDecodeError: {exc}"
        else:
            if isinstance(parsed_ruff, list):
                ruff_findings = parsed_ruff
            else:
                ruff_parse_error = (
                    "TypeError: Ruff JSON output was not a list."
                )

    mypy_args = [
        "mypy",
        "--python-version",
        "3.11",
        "--ignore-missing-imports",
        "--follow-imports=silent",
    ]
    if bool(contract["mypy"].get("explicit_package_bases", False)):
        mypy_args.append("--explicit-package-bases")
    mypy_args.extend(
        [
            "--show-error-codes",
            "--no-color-output",
            *mypy_files,
        ]
    )
    mypy = _run(mypy_args)
    mypy_findings = _parse_mypy_findings(mypy.stdout)

    report: dict[str, Any] = {
        "audit_id": str(
            contract.get(
                "audit_id",
                "stage9.5-5-static-software-assurance-v1_4-discovery",
            )
        ),
        "contract": str(contract_path.relative_to(PROJECT_ROOT)),
        "historical_runtime_lock": {
            "path": str(lock.relative_to(PROJECT_ROOT)),
            "expected_raw_sha256": contract["historical_runtime_lock"]["raw_sha256"],
            "actual_raw_sha256": lock_sha,
            "identity_matches": lock_sha
            == contract["historical_runtime_lock"]["raw_sha256"],
        },
        "developer_tools": {
            "ruff": ruff_version,
            "mypy": mypy_version,
        },
        "scope": {
            "ruff_file_count": len(ruff_files),
            "mypy_file_count": len(mypy_files),
            "missing_files": missing_files,
        },
        "ruff": {
            "returncode": ruff.returncode,
            "finding_count": len(ruff_findings),
            "findings": ruff_findings,
            "parse_error": ruff_parse_error,
            "stderr": ruff.stderr[-12000:],
        },
        "mypy": {
            "returncode": mypy.returncode,
            "finding_count": len(mypy_findings),
            "findings": mypy_findings,
            "stdout": mypy.stdout[-30000:],
            "stderr": mypy.stderr[-12000:],
        },
        "triage_status": "pending" if ruff_findings or mypy_findings else "not_required",
        "production_sources_rewritten": False,
        "historical_runtime_lock_rewritten": False,
        "stage10_outcomes_accessed": False,
    }

    tool_execution_valid = bool(
        ruff_version["matches"]
        and mypy_version["matches"]
        and not missing_files
        and ruff_parse_error is None
        and ruff.returncode in (0, 1)
        and mypy.returncode in (0, 1)
        and report["historical_runtime_lock"]["identity_matches"]
    )
    no_findings = not ruff_findings and not mypy_findings
    report["tool_execution_valid"] = tool_execution_valid
    report["pass"] = bool(tool_execution_valid and no_findings)
    report["status"] = (
        "pass"
        if report["pass"]
        else ("triage_required" if tool_execution_valid else "tooling_error")
    )
    report["canonical_sha256"] = _canonical_sha256(
        {k: v for k, v in report.items() if k != "canonical_sha256"}
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "static_assurance_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage 9.5-5 Static Software Assurance",
        "",
        f"- status: **{report['status'].upper()}**",
        f"- Ruff findings: **{len(ruff_findings)}**",
        f"- mypy findings: **{len(mypy_findings)}**",
        f"- Ruff scope files: **{len(ruff_files)}**",
        f"- mypy scope files: **{len(mypy_files)}**",
        f"- historical lock identity: **{'MATCH' if report['historical_runtime_lock']['identity_matches'] else 'MISMATCH'}**",
        f"- report canonical SHA-256: `{report['canonical_sha256']}`",
        "",
        "## Triage",
        "",
        (
            "- no findings"
            if no_findings
            else "- required before Stage 9.5-5 closure"
        ),
    ]
    (output_dir / "STATIC_ASSURANCE_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    if not report["pass"]:
        raise SystemExit(
            "Stage 9.5-5 discovery did not close cleanly: "
            f"status={report['status']}, "
            f"ruff={len(ruff_findings)}, mypy={len(mypy_findings)}"
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Stage 9.5-5 static software assurance discovery"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_static_v1_4"),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=CONTRACT_PATH,
    )
    args = parser.parse_args()
    run(args.output_dir, contract_path=args.contract)


if __name__ == "__main__":
    main()
