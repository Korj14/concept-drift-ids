from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "stage9_5_6_closure_order_gate_v1.json"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def _canonical_json_hash(payload: object) -> str:
    data = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"Duplicate JSON object key: {key}")
        payload[key] = value
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
    )
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return payload


def _get_path(payload: dict[str, Any], dotted: str) -> Any:
    node: Any = payload
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def evaluate(
    *,
    contract_path: Path = CONTRACT_PATH,
    closure_doc: Path | None = None,
    success_json: Path | None = None,
    evidence_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    contract = _load_json(contract_path)
    closure = (
        closure_doc
        if closure_doc is not None
        else PROJECT_ROOT / str(contract["closure_doc_path"])
    )
    success = (
        success_json
        if success_json is not None
        else PROJECT_ROOT / str(contract["success_json_path"])
    )

    report: dict[str, Any] = {
        "contract_id": contract["contract_id"],
        "closure_doc": str(closure),
        "success_json": str(success),
        "later_packages_unlocked": False,
        "failures": [],
    }

    if not closure.is_file():
        report["failures"].append("closure_doc_missing")
    if not success.is_file():
        report["failures"].append("success_json_missing")
    if report["failures"]:
        return report

    try:
        success_payload = _load_json(success)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        report["failures"].append(f"success_json_invalid:{type(exc).__name__}")
        return report

    for dotted, expected in contract["required_success_values"].items():
        try:
            actual = _get_path(success_payload, dotted)
        except KeyError:
            report["failures"].append(f"missing_success_field:{dotted}")
            continue
        if actual != expected:
            report["failures"].append(f"success_value_mismatch:{dotted}")

    for dotted in contract.get("required_sha40_fields", []):
        try:
            value = _get_path(success_payload, dotted)
        except KeyError:
            report["failures"].append(f"missing_success_sha40_field:{dotted}")
            continue
        if not isinstance(value, str) or SHA40_RE.fullmatch(value) is None:
            report["failures"].append(f"invalid_success_sha40:{dotted}")

    for pair in contract.get("required_equal_fields", []):
        if not isinstance(pair, list) or len(pair) != 2:
            report["failures"].append("invalid_contract_equal_field_pair")
            continue
        left_name, right_name = pair
        try:
            left = _get_path(success_payload, left_name)
            right = _get_path(success_payload, right_name)
        except KeyError as exc:
            report["failures"].append(f"missing_equal_field:{exc.args[0]}")
            continue
        if left != right:
            report["failures"].append(
                f"success_field_mismatch:{left_name}!={right_name}"
            )

    for dotted in contract.get("required_git_ancestor_fields", []):
        try:
            value = _get_path(success_payload, dotted)
        except KeyError:
            report["failures"].append(f"missing_git_ancestor_field:{dotted}")
            continue
        if not isinstance(value, str) or SHA40_RE.fullmatch(value) is None:
            report["failures"].append(f"invalid_git_ancestor_sha:{dotted}")
            continue
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", value, "HEAD"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            report["failures"].append(f"audited_head_not_ancestor:{dotted}")

    report_hashes: list[str] = []
    for dotted in contract["required_success_hash_fields"]:
        try:
            value = _get_path(success_payload, dotted)
        except KeyError:
            report["failures"].append(f"missing_success_hash_field:{dotted}")
            continue
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            report["failures"].append(f"invalid_success_sha256:{dotted}")
            continue
        report_hashes.append(value)

    resolved_root = evidence_root.resolve()
    for binding in contract.get("required_canonical_json_reports", []):
        if not isinstance(binding, dict):
            report["failures"].append("invalid_contract_report_binding")
            continue
        relative = binding.get("path")
        hash_field = binding.get("success_hash_field")
        embedded_hash_field = binding.get("embedded_hash_field")
        required_values = binding.get("required_values", {})
        if (
            not isinstance(relative, str)
            or not isinstance(hash_field, str)
            or not isinstance(embedded_hash_field, str)
            or not isinstance(required_values, dict)
        ):
            report["failures"].append("invalid_contract_report_binding")
            continue

        relative_path = Path(relative)
        if relative_path.is_absolute():
            report["failures"].append(f"report_path_not_repository_relative:{relative}")
            continue
        report_path = (resolved_root / relative_path).resolve()
        if not report_path.is_relative_to(resolved_root):
            report["failures"].append(f"report_path_escapes_repository:{relative}")
            continue
        if not report_path.is_file():
            report["failures"].append(f"required_report_missing:{relative}")
            continue

        try:
            report_payload = _load_json(report_path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            report["failures"].append(
                f"required_report_invalid:{relative}:{type(exc).__name__}"
            )
            continue

        try:
            expected_hash = _get_path(success_payload, hash_field)
        except KeyError:
            report["failures"].append(f"missing_success_hash_field:{hash_field}")
            continue
        embedded_hash = report_payload.get(embedded_hash_field)
        core = dict(report_payload)
        core.pop(embedded_hash_field, None)
        try:
            actual_hash = _canonical_json_hash(core)
        except (TypeError, ValueError) as exc:
            report["failures"].append(
                f"required_report_not_canonicalizable:{relative}:"
                f"{type(exc).__name__}"
            )
            actual_hash = None
        if (
            not isinstance(expected_hash, str)
            or SHA256_RE.fullmatch(expected_hash) is None
            or embedded_hash != expected_hash
            or actual_hash != expected_hash
        ):
            report["failures"].append(f"required_report_hash_mismatch:{relative}")

        for dotted, expected in required_values.items():
            try:
                actual = _get_path(report_payload, dotted)
            except KeyError:
                report["failures"].append(
                    f"required_report_missing_field:{relative}:{dotted}"
                )
                continue
            if actual != expected:
                report["failures"].append(
                    f"required_report_value_mismatch:{relative}:{dotted}"
                )

        for pair in binding.get("required_equal_success_fields", []):
            if not isinstance(pair, list) or len(pair) != 2:
                report["failures"].append(
                    f"invalid_report_success_equal_field_pair:{relative}"
                )
                continue
            report_field, success_field = pair
            if not isinstance(report_field, str) or not isinstance(success_field, str):
                report["failures"].append(
                    f"invalid_report_success_equal_field_pair:{relative}"
                )
                continue
            try:
                report_value = _get_path(report_payload, report_field)
            except KeyError:
                report["failures"].append(
                    f"required_report_missing_field:{relative}:{report_field}"
                )
                continue
            try:
                success_value = _get_path(success_payload, success_field)
            except KeyError:
                report["failures"].append(
                    f"missing_success_field:{success_field}"
                )
                continue
            if report_value != success_value:
                report["failures"].append(
                    f"report_success_field_mismatch:{relative}:"
                    f"{report_field}!={success_field}"
                )

        for pair in binding.get("required_report_ancestor_success_fields", []):
            if not isinstance(pair, list) or len(pair) != 2:
                report["failures"].append(
                    f"invalid_report_success_ancestor_field_pair:{relative}"
                )
                continue
            report_field, success_field = pair
            if not isinstance(report_field, str) or not isinstance(success_field, str):
                report["failures"].append(
                    f"invalid_report_success_ancestor_field_pair:{relative}"
                )
                continue
            try:
                report_value = _get_path(report_payload, report_field)
            except KeyError:
                report["failures"].append(
                    f"required_report_missing_field:{relative}:{report_field}"
                )
                continue
            try:
                success_value = _get_path(success_payload, success_field)
            except KeyError:
                report["failures"].append(
                    f"missing_success_field:{success_field}"
                )
                continue
            if (
                not isinstance(report_value, str)
                or SHA40_RE.fullmatch(report_value) is None
                or not isinstance(success_value, str)
                or SHA40_RE.fullmatch(success_value) is None
            ):
                report["failures"].append(
                    f"invalid_report_success_ancestor_sha:{relative}:"
                    f"{report_field}->{success_field}"
                )
                continue
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", report_value, success_value],
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                report["failures"].append(
                    f"report_head_not_ancestor:{relative}:"
                    f"{report_field}->{success_field}"
                )

    try:
        closure_text = closure.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        report["failures"].append(f"closure_doc_invalid:{type(exc).__name__}")
        return report

    for marker in contract["closure_doc_must_reference"]:
        if marker not in closure_text:
            report["failures"].append(f"closure_doc_missing_reference:{marker}")

    if contract.get("closure_doc_must_contain_report_canonical_sha256", False):
        for value in report_hashes:
            if value not in closure_text:
                report["failures"].append(
                    "closure_doc_missing_report_canonical_sha256"
                )

    report["later_packages_unlocked"] = not report["failures"]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail-closed Stage 9.5-6 predecessor closure gate"
    )
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--closure-doc", type=Path, default=None)
    parser.add_argument("--success-json", type=Path, default=None)
    parser.add_argument("--report-path", type=Path, default=None)
    args = parser.parse_args()

    report = evaluate(
        contract_path=args.contract,
        closure_doc=args.closure_doc,
        success_json=args.success_json,
    )
    if args.report_path is not None:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    value = "true" if report["later_packages_unlocked"] else "false"
    print(f"later_packages_unlocked={value}")
    if report["failures"]:
        print("Stage 9.5-7/8/9 remain locked: " + "; ".join(report["failures"]))


if __name__ == "__main__":
    main()
