from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np
import pandas as pd

from concept_drift_ids.cd_runtime import verify_locked_distributions

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "stage9_5_6_stage1_reconstruction_evidence_v1.json"
)
DEFAULT_RECONSTRUCTED_ROOT = (
    PROJECT_ROOT
    / "artifacts"
    / "stage9_5_stage1_reconstruction_v1"
    / "interim"
    / "cicids2017"
)
DEFAULT_REPORT_PATH = (
    PROJECT_ROOT
    / "results"
    / "audits"
    / "stage9_5_full_seed_rerun_v1"
    / "stage1_reconstruction_report.json"
)

METADATA_COLUMNS = ["source_file", "source_order", "row_in_source"]
LABEL_NORMALIZATION = {
    "Web Attack \uFFFD Brute Force": "Web Attack - Brute Force",
    "Web Attack \uFFFD XSS": "Web Attack - XSS",
    "Web Attack \uFFFD Sql Injection": "Web Attack - SQL Injection",
}
PRIMARY_DUPLICATE_COLUMN = "Fwd Header Length"
SECONDARY_DUPLICATE_COLUMN = "Fwd Header Length.1"


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


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_text_sha256(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        value = raw.decode("utf-8-sig")
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        value = raw.decode("utf-16")
    else:
        value = raw.decode("utf-8")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _git_show_bytes(commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324


def _historical_namespace(contract: dict[str, Any]) -> SimpleNamespace:
    environment = contract["historical_environment"]
    if not isinstance(environment, dict):
        raise TypeError("historical_environment must be an object")
    replay_head = str(environment["replay_head"])
    preprocessing_path = str(environment["preprocessing_path"])
    expected_blob = str(environment["preprocessing_git_blob_sha1"])

    source = _git_show_bytes(replay_head, preprocessing_path)
    observed_blob = _git_blob_sha1(source)
    if observed_blob != expected_blob:
        raise ValueError(
            "Historical preprocessing Git blob identity mismatch: "
            f"expected {expected_blob}, got {observed_blob}"
        )

    namespace: dict[str, Any] = {
        "__name__": "stage9_5_historical_preprocessing",
        "__file__": str(PROJECT_ROOT / preprocessing_path),
    }
    code = compile(
        source.decode("utf-8"),
        str(PROJECT_ROOT / preprocessing_path),
        "exec",
    )
    exec(code, namespace)  # noqa: S102

    expected_constants = {
        "METADATA_COLUMNS": METADATA_COLUMNS,
        "LABEL_NORMALIZATION": LABEL_NORMALIZATION,
        "PRIMARY_DUPLICATE_COLUMN": PRIMARY_DUPLICATE_COLUMN,
        "SECONDARY_DUPLICATE_COLUMN": SECONDARY_DUPLICATE_COLUMN,
    }
    for name, expected in expected_constants.items():
        if namespace.get(name) != expected:
            raise ValueError(f"Historical preprocessing constant mismatch: {name}")

    return SimpleNamespace(**namespace)


def _verify_environment(contract: dict[str, Any]) -> dict[str, Any]:
    environment = contract["historical_environment"]
    if not isinstance(environment, dict):
        raise TypeError("historical_environment must be an object")

    expected_python = str(environment["python_version"])
    observed_python = platform.python_version()
    if observed_python != expected_python:
        raise RuntimeError(
            "Historical Python version mismatch: "
            f"expected {expected_python}, got {observed_python}"
        )

    lock_path = PROJECT_ROOT / "requirements-lock.txt"
    expected_raw = str(environment["requirements_lock_sha256"])
    observed_raw = _sha256_file(lock_path)
    if observed_raw != expected_raw:
        raise ValueError(
            "Frozen dependency lock raw SHA-256 mismatch: "
            f"expected {expected_raw}, got {observed_raw}"
        )

    expected_normalized = str(
        environment["requirements_lock_normalized_text_sha256"]
    )
    observed_normalized = _normalized_text_sha256(lock_path)
    if observed_normalized != expected_normalized:
        raise ValueError(
            "Frozen dependency lock normalized-text SHA-256 mismatch: "
            f"expected {expected_normalized}, got {observed_normalized}"
        )

    installed = verify_locked_distributions(lock_path=lock_path)
    return {
        "python_version": observed_python,
        "requirements_lock_sha256": observed_raw,
        "requirements_lock_normalized_text_sha256": observed_normalized,
        "installed_distributions": installed,
        "installed_distributions_sha256": _canonical_sha256(installed),
    }


def _independent_preprocess_file(
    path: Path,
    source_order: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = pd.read_csv(path, low_memory=False)
    original_rows = len(df)
    original_columns = len(df.columns)

    df = df.copy()
    df.columns = [str(column).strip() for column in df.columns]

    if PRIMARY_DUPLICATE_COLUMN not in df.columns:
        raise ValueError(f"Expected column missing: {PRIMARY_DUPLICATE_COLUMN}")
    if SECONDARY_DUPLICATE_COLUMN not in df.columns:
        raise ValueError(
            "Expected duplicated CICIDS2017 feature missing: "
            f"{SECONDARY_DUPLICATE_COLUMN}"
        )
    if not df[PRIMARY_DUPLICATE_COLUMN].equals(
        df[SECONDARY_DUPLICATE_COLUMN]
    ):
        raise ValueError("Duplicated Fwd Header Length columns differ")
    df = df.drop(columns=[SECONDARY_DUPLICATE_COLUMN])

    if "Label" not in df.columns:
        raise ValueError("Label column is missing")
    if df["Label"].isna().any():
        raise ValueError("Missing labels detected")
    df["Label"] = (
        df["Label"]
        .astype("string")
        .str.strip()
        .replace(LABEL_NORMALIZATION)
    )

    feature_columns = [
        column for column in df.columns if column != "Label"
    ]
    non_numeric = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(df[column])
    ]
    if non_numeric:
        raise TypeError(
            "Non-numeric model features detected: " + ", ".join(non_numeric)
        )

    df.loc[:, feature_columns] = df.loc[:, feature_columns].replace(
        [np.inf, -np.inf],
        np.nan,
    )

    missing_rows = int(
        df.drop(columns=["Label"]).isna().any(axis=1).sum()
    )
    missing_cells = int(
        df.drop(columns=["Label"]).isna().sum().sum()
    )
    duplicate_rows = int(
        df.duplicated(
            subset=[
                column for column in df.columns if column != "Label"
            ],
            keep="first",
        ).sum()
    )
    label_counts = {
        str(label): int(count)
        for label, count in df["Label"].value_counts(dropna=False).items()
    }

    df.insert(
        0,
        "row_in_source",
        np.arange(len(df), dtype=np.int64),
    )
    df.insert(0, "source_order", source_order)
    df.insert(0, "source_file", path.name)

    model_features = [
        column
        for column in df.columns
        if column not in set(METADATA_COLUMNS + ["Label"])
    ]
    report = {
        "source_file": path.name,
        "source_order": source_order,
        "original_rows": original_rows,
        "original_columns": original_columns,
        "rows_after_structural_preprocessing": len(df),
        "columns_after_structural_preprocessing": len(df.columns),
        "model_feature_count": len(model_features),
        "missing_feature_rows_after_inf_conversion": missing_rows,
        "missing_feature_cells_after_inf_conversion": missing_cells,
        "duplicate_feature_rows_retained": duplicate_rows,
        "labels": label_counts,
    }
    return df, report


def _assert_semantic_equal(
    reconstructed: pd.DataFrame,
    independent: pd.DataFrame,
) -> None:
    pd.testing.assert_frame_equal(
        reconstructed,
        independent,
        check_dtype=False,
        check_exact=True,
        check_names=True,
        check_like=False,
    )


def _decompressed_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_preprocessing_manifest(
    *,
    reports: list[dict[str, Any]],
    feature_columns: list[str],
) -> dict[str, Any]:
    return {
        "dataset": "CICIDS2017",
        "processing_stage": "structural_preprocessing",
        "files_processed": len(reports),
        "label_normalization": LABEL_NORMALIZATION,
        "dropped_duplicate_feature": SECONDARY_DUPLICATE_COLUMN,
        "metadata_columns": METADATA_COLUMNS,
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "files": reports,
    }


def _write_historical_manifest(
    path: Path,
    payload: dict[str, Any],
) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _verify_raw_manifest(
    contract: dict[str, Any],
) -> dict[str, Any]:
    raw_contract = contract["raw_input_contract"]
    if not isinstance(raw_contract, dict):
        raise TypeError("raw_input_contract must be an object")
    manifest_path = PROJECT_ROOT / str(raw_contract["manifest_path"])
    manifest = _load_json(manifest_path)
    observed = _canonical_sha256(manifest)
    expected = str(raw_contract["manifest_canonical_sha256"])
    if observed != expected:
        raise ValueError(
            "Raw manifest canonical SHA-256 mismatch: "
            f"expected {expected}, got {observed}"
        )
    return manifest


def _empty_report(contract: dict[str, Any]) -> dict[str, Any]:
    required = contract["required_report"]
    verifier = contract["verifier_implementation"]
    if not isinstance(required, dict):
        raise TypeError("required_report must be an object")
    if not isinstance(verifier, dict):
        raise TypeError("verifier_implementation must be an object")
    verifier_id = verifier.get("verifier_id")
    if not isinstance(verifier_id, str) or not verifier_id:
        raise TypeError("verifier_implementation.verifier_id must be a string")
    return {
        "audit_id": required["audit_id"],
        "contract_id": contract["contract_id"],
        "contract_canonical_sha256": _canonical_sha256(contract),
        "verifier_id": verifier_id,
        "verifier_source_sha256": _sha256_file(Path(__file__)),
        "status": "blocked",
        "pass": False,
        "repository_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "manual_success_override_permitted": False,
        "raw_file_count_verified": 0,
        "interim_table_count_verified": 0,
        "preprocessing_manifest_canonical_sha256": None,
        "semantic_mismatch_count": 0,
        "tables": [],
        "failures": [],
        "blockers": [],
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    core = dict(report)
    core.pop("canonical_sha256", None)
    report["canonical_sha256"] = _canonical_sha256(core)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run(
    *,
    raw_root: Path,
    reconstructed_root: Path = DEFAULT_RECONSTRUCTED_ROOT,
    report_path: Path = DEFAULT_REPORT_PATH,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    contract = _load_json(contract_path)
    report = _empty_report(contract)

    try:
        report["environment"] = _verify_environment(contract)
        historical = _historical_namespace(contract)
        raw_manifest = _verify_raw_manifest(contract)
    except (
        FileNotFoundError,
        RuntimeError,
        subprocess.CalledProcessError,
        TypeError,
        ValueError,
    ) as exc:
        report["failures"].append(
            f"preflight:{type(exc).__name__}:{exc}"
        )
        _write_report(report_path, report)
        return report

    if reconstructed_root.exists() and any(reconstructed_root.iterdir()):
        report["failures"].append("reconstructed_output_root_not_empty")
        _write_report(report_path, report)
        return report
    reconstructed_root.mkdir(parents=True, exist_ok=True)

    raw_contract = contract["raw_input_contract"]
    accepted = contract["accepted_stage1_identity"]
    if not isinstance(raw_contract, dict) or not isinstance(accepted, dict):
        report["failures"].append("contract_structure_invalid")
        _write_report(report_path, report)
        return report

    expected_hashes = raw_contract["exact_file_sha256"]
    if not isinstance(expected_hashes, dict):
        report["failures"].append("raw_hash_contract_not_object")
        _write_report(report_path, report)
        return report

    file_order = raw_manifest.get("file_order")
    if not isinstance(file_order, list):
        report["failures"].append("raw_manifest_file_order_missing")
        _write_report(report_path, report)
        return report
    if file_order != list(expected_hashes):
        report["failures"].append("raw_manifest_file_order_contract_mismatch")
        _write_report(report_path, report)
        return report

    historical_expected_files = getattr(historical, "EXPECTED_FILES", None)
    if historical_expected_files != file_order:
        report["failures"].append("historical_expected_files_mismatch")
        _write_report(report_path, report)
        return report

    reports: list[dict[str, Any]] = []
    reference_features: list[str] | None = None

    preprocess_file = getattr(historical, "preprocess_file", None)
    get_feature_columns = getattr(historical, "get_feature_columns", None)
    if not callable(preprocess_file) or not callable(get_feature_columns):
        report["failures"].append("historical_preprocessing_api_missing")
        _write_report(report_path, report)
        return report

    for source_order, filename in enumerate(file_order):
        raw_path = raw_root / str(filename)
        expected_sha = str(expected_hashes[filename])
        if not raw_path.is_file():
            report["failures"].append(f"raw_file_missing:{filename}")
            continue
        actual_sha = _sha256_file(raw_path)
        if actual_sha != expected_sha:
            report["failures"].append(
                f"raw_file_sha256_mismatch:{filename}"
            )
            continue
        report["raw_file_count_verified"] += 1

        try:
            historical_df, historical_report = preprocess_file(
                raw_path,
                source_order,
            )
            if not isinstance(historical_df, pd.DataFrame):
                raise TypeError("Historical preprocess_file did not return DataFrame")
            if not isinstance(historical_report, dict):
                raise TypeError("Historical preprocess_file report is not object")

            historical_features = list(get_feature_columns(historical_df))
            if reference_features is None:
                reference_features = historical_features
            elif historical_features != reference_features:
                raise ValueError(
                    f"Historical feature schema mismatch: {filename}"
                )

            output_path = (
                reconstructed_root / f"{raw_path.stem}.csv.gz"
            )
            historical_df.to_csv(
                output_path,
                index=False,
                compression="gzip",
            )
            del historical_df

            reconstructed = pd.read_csv(
                output_path,
                low_memory=False,
            )
            independent, independent_report = _independent_preprocess_file(
                raw_path,
                source_order,
            )

            _assert_semantic_equal(reconstructed, independent)
            if historical_report != independent_report:
                raise ValueError(
                    "Historical and independent preprocessing reports differ"
                )
            independent_features = [
                column
                for column in independent.columns
                if column not in set(METADATA_COLUMNS + ["Label"])
            ]
            if independent_features != reference_features:
                raise ValueError(
                    f"Independent feature schema mismatch: {filename}"
                )
            if len(independent_features) != int(
                accepted["model_feature_count"]
            ):
                raise ValueError(
                    f"Model feature count mismatch: {filename}"
                )

            report["interim_table_count_verified"] += 1
            reports.append(dict(historical_report))
            report["tables"].append(
                {
                    "source_file": filename,
                    "source_order": source_order,
                    "row_count": len(reconstructed),
                    "column_count": len(reconstructed.columns),
                    "model_feature_count": len(independent_features),
                    "decompressed_csv_sha256": _decompressed_sha256(
                        output_path
                    ),
                    "semantic_equal_to_independent_recompute": True,
                }
            )
            del reconstructed
            del independent
        except (
            AssertionError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            report["semantic_mismatch_count"] += 1
            report["failures"].append(
                f"table_verification:{filename}:{type(exc).__name__}:{exc}"
            )

    manifest = _build_preprocessing_manifest(
        reports=reports,
        feature_columns=reference_features or [],
    )
    manifest_path = reconstructed_root / "preprocessing_manifest.json"
    _write_historical_manifest(manifest_path, manifest)
    manifest_canonical = _canonical_sha256(manifest)
    report["preprocessing_manifest_canonical_sha256"] = manifest_canonical
    report["preprocessing_manifest_file_sha256"] = _sha256_file(manifest_path)

    required_success = contract["required_report"]["required_success_values"]
    if not isinstance(required_success, dict):
        report["failures"].append("required_success_values_not_object")
    else:
        checks = {
            "raw_file_count_verified": report["raw_file_count_verified"],
            "interim_table_count_verified": report[
                "interim_table_count_verified"
            ],
            "preprocessing_manifest_canonical_sha256": manifest_canonical,
            "semantic_mismatch_count": report["semantic_mismatch_count"],
        }
        for field, actual in checks.items():
            expected = required_success[field]
            if actual != expected:
                report["failures"].append(
                    f"required_success_mismatch:{field}"
                )

    report["pass"] = not report["failures"] and not report["blockers"]
    report["status"] = "pass" if report["pass"] else "blocked"
    _write_report(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Stage 9.5-6 Stage-1 historical reconstruction evidence"
        )
    )
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument(
        "--reconstructed-root",
        type=Path,
        default=DEFAULT_RECONSTRUCTED_ROOT,
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=CONTRACT_PATH,
    )
    args = parser.parse_args()

    result = run(
        raw_root=args.raw_root,
        reconstructed_root=args.reconstructed_root,
        report_path=args.report,
        contract_path=args.contract,
    )
    if not result["pass"]:
        raise SystemExit(
            "Stage 9.5-6 Stage-1 reconstruction evidence blocked: "
            + "; ".join(str(item) for item in result["failures"])
        )


if __name__ == "__main__":
    main()
