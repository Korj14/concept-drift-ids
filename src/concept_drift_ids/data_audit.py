from __future__ import annotations

import csv
import gc
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cicids2017"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "results"
    / "data_audit"
)

MANIFEST_DIR = (
    PROJECT_ROOT
    / "data"
    / "manifests"
)

PERMANENT_MANIFEST_PATH = (
    MANIFEST_DIR
    / "cicids2017_raw_manifest.json"
)


EXPECTED_FILES = [
    "Monday-WorkingHours.pcap_ISCX.csv",
    "Tuesday-WorkingHours.pcap_ISCX.csv",
    "Wednesday-workingHours.pcap_ISCX.csv",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
]


def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """
    Compute a SHA-256 digest for the exact raw file bytes.

    This allows later experiments to prove exactly which dataset
    files were used.
    """
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def read_raw_header(
    path: Path,
) -> list[str]:
    """
    Read the original CSV header without allowing pandas to rename
    duplicate column names.
    """
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as file:
        reader = csv.reader(file)
        return next(reader)


def duplicate_header_names(
    header: list[str],
) -> dict[str, int]:
    """
    Return duplicate header names after stripping surrounding
    whitespace.
    """
    cleaned = [
        name.strip()
        for name in header
    ]

    counts = Counter(cleaned)

    return {
        name: count
        for name, count in counts.items()
        if count > 1
    }


def inspect_file(
    path: Path,
) -> tuple[
    dict,
    pd.DataFrame,
    dict,
]:
    """
    Audit one raw CICIDS2017 CSV without modifying it.

    Returns:
        audit result
        label-count DataFrame
        compact permanent-manifest record
    """
    print(f"\nAuditing: {path.name}")

    file_size_bytes = path.stat().st_size

    print("  computing SHA-256...")
    sha256 = sha256_file(path)

    raw_header = read_raw_header(path)

    normalized_raw_header = [
        column.strip()
        for column in raw_header
    ]

    duplicate_headers = (
        duplicate_header_names(
            raw_header
        )
    )

    # Load exactly one source file at a time.
    df = pd.read_csv(
        path,
        low_memory=False,
    )

    # CICIDS2017 headers contain leading spaces.
    # pandas may also rename duplicate headers using ".1".
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    if "Label" not in df.columns:
        raise ValueError(
            f"'Label' column not found in "
            f"{path.name}"
        )

    row_count = len(df)

    pandas_column_count = len(
        df.columns
    )

    # ---------------------------------------------------------
    # Label distribution
    # ---------------------------------------------------------
    label_counts = (
        df["Label"]
        .value_counts(
            dropna=False
        )
        .rename_axis("label")
        .reset_index(
            name="count"
        )
    )

    label_counts.insert(
        0,
        "source_file",
        path.name,
    )

    label_counts[
        "contains_replacement_character"
    ] = (
        label_counts["label"]
        .astype(str)
        .str.contains(
            "\uFFFD",
            regex=False,
        )
    )

    raw_label_counts = {
        str(label): int(count)
        for label, count in (
            df["Label"]
            .value_counts(
                dropna=False
            )
            .items()
        )
    }

    # ---------------------------------------------------------
    # Missing values
    # ---------------------------------------------------------
    missing_by_column = (
        df.isna().sum()
    )

    total_missing_cells = int(
        missing_by_column.sum()
    )

    # pandas 3.x Copy-on-Write can expose a read-only NumPy view.
    # We intentionally create a writable copy because this mask is
    # extended as infinity values are identified.
    invalid_row_mask = (
        df.isna()
        .any(axis=1)
        .to_numpy(
            copy=True
        )
    )

    # ---------------------------------------------------------
    # Infinity values
    # ---------------------------------------------------------
    positive_inf_cells = 0
    negative_inf_cells = 0

    inf_by_column: dict[
        str,
        dict[str, int],
    ] = {}

    numeric_columns = (
        df.select_dtypes(
            include=[np.number]
        )
        .columns
    )

    for column in numeric_columns:
        values = (
            df[column]
            .to_numpy()
        )

        positive_mask = (
            np.isposinf(values)
        )

        negative_mask = (
            np.isneginf(values)
        )

        positive_count = int(
            positive_mask.sum()
        )

        negative_count = int(
            negative_mask.sum()
        )

        if (
            positive_count
            or negative_count
        ):
            inf_by_column[column] = {
                "positive_infinity": (
                    positive_count
                ),
                "negative_infinity": (
                    negative_count
                ),
            }

        positive_inf_cells += (
            positive_count
        )

        negative_inf_cells += (
            negative_count
        )

        # Deliberately avoid in-place mutation of an array that
        # might originate from pandas Copy-on-Write behavior.
        invalid_row_mask = (
            invalid_row_mask
            | positive_mask
            | negative_mask
        )

    invalid_rows = int(
        invalid_row_mask.sum()
    )

    # ---------------------------------------------------------
    # Exact duplicate rows within this raw source file
    # ---------------------------------------------------------
    duplicate_rows = int(
        df.duplicated(
            keep="first"
        ).sum()
    )

    # ---------------------------------------------------------
    # Features constant within this source file
    # ---------------------------------------------------------
    constant_columns = []

    for column in df.columns:
        if column == "Label":
            continue

        if (
            df[column]
            .nunique(
                dropna=False
            )
            <= 1
        ):
            constant_columns.append(
                column
            )

    # ---------------------------------------------------------
    # Benign / attack counts
    # ---------------------------------------------------------
    labels_stripped = (
        df["Label"]
        .astype(str)
        .str.strip()
    )

    benign_rows = int(
        (
            labels_stripped
            == "BENIGN"
        ).sum()
    )

    attack_rows = (
        row_count
        - benign_rows
    )

    attack_share = (
        attack_rows / row_count
        if row_count
        else 0.0
    )

    memory_mb = (
        df.memory_usage(
            index=True,
            deep=True,
        ).sum()
        / (1024 ** 2)
    )

    # ---------------------------------------------------------
    # Detailed audit information
    # ---------------------------------------------------------
    summary = {
        "source_file": path.name,
        "file_size_bytes": (
            file_size_bytes
        ),
        "file_size_mb": round(
            file_size_bytes
            / (1024 ** 2),
            2,
        ),
        "sha256": sha256,
        "rows": row_count,
        "raw_columns": len(
            raw_header
        ),
        "pandas_columns": (
            pandas_column_count
        ),
        "benign_rows": (
            benign_rows
        ),
        "attack_rows": (
            attack_rows
        ),
        "attack_share": (
            attack_share
        ),
        "missing_cells": (
            total_missing_cells
        ),
        "positive_infinity_cells": (
            positive_inf_cells
        ),
        "negative_infinity_cells": (
            negative_inf_cells
        ),
        "invalid_rows": (
            invalid_rows
        ),
        "duplicate_rows": (
            duplicate_rows
        ),
        "constant_feature_count": (
            len(constant_columns)
        ),
        "memory_mb": round(
            memory_mb,
            2,
        ),
    }

    details = {
        "source_file": path.name,
        "file_size_bytes": (
            file_size_bytes
        ),
        "sha256": sha256,
        "raw_header": (
            raw_header
        ),
        "normalized_raw_header": (
            normalized_raw_header
        ),
        "duplicate_raw_headers": (
            duplicate_headers
        ),
        "missing_by_column": {
            str(column): int(count)
            for column, count
            in missing_by_column.items()
            if count > 0
        },
        "infinity_by_column": (
            inf_by_column
        ),
        "constant_features": (
            constant_columns
        ),
        "dtypes": {
            str(column): str(dtype)
            for column, dtype
            in df.dtypes.items()
        },
    }

    # ---------------------------------------------------------
    # Compact permanent provenance record
    # ---------------------------------------------------------
    manifest_record = {
        "source_file": path.name,
        "file_size_bytes": (
            file_size_bytes
        ),
        "sha256": sha256,
        "rows": row_count,
        "raw_columns": len(
            raw_header
        ),
        "raw_label_counts": (
            raw_label_counts
        ),
    }

    print(
        f"  SHA-256:           "
        f"{sha256}"
    )

    print(
        f"  rows:              "
        f"{row_count:,}"
    )

    print(
        f"  raw columns:       "
        f"{len(raw_header)}"
    )

    print(
        f"  attack rows:       "
        f"{attack_rows:,}"
    )

    print(
        f"  benign rows:       "
        f"{benign_rows:,}"
    )

    print(
        f"  invalid rows:      "
        f"{invalid_rows:,}"
    )

    print(
        f"  duplicate rows:    "
        f"{duplicate_rows:,}"
    )

    print(
        f"  duplicate headers: "
        f"{duplicate_headers}"
    )

    del df
    gc.collect()

    return (
        {
            "summary": summary,
            "details": details,
        },
        label_counts,
        manifest_record,
    )


def main() -> None:
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            "CICIDS2017 directory does not exist:\n"
            f"{DATA_DIR}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # This is the folder you create once.
    # The script writes the manifest file itself.
    MANIFEST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    missing_files = [
        filename
        for filename in EXPECTED_FILES
        if not (
            DATA_DIR / filename
        ).exists()
    ]

    if missing_files:
        formatted = "\n".join(
            f"  - {name}"
            for name in missing_files
        )

        raise FileNotFoundError(
            "Expected CICIDS2017 files are missing:\n"
            f"{formatted}"
        )

    unexpected_csvs = sorted(
        path.name
        for path in DATA_DIR.glob(
            "*.csv"
        )
        if path.name
        not in EXPECTED_FILES
    )

    if unexpected_csvs:
        print(
            "\nWarning: additional CSV "
            "files found:"
        )

        for filename in unexpected_csvs:
            print(
                f"  - {filename}"
            )

    summaries = []
    details = []
    label_tables = []
    manifest_records = []

    reference_schema = None
    schemas_match = True

    print("=" * 72)
    print(
        "CICIDS2017 RAW DATA AUDIT"
    )
    print("=" * 72)

    print(
        f"Dataset directory: "
        f"{DATA_DIR}"
    )

    print(
        f"Expected files:    "
        f"{len(EXPECTED_FILES)}"
    )

    for filename in EXPECTED_FILES:
        path = DATA_DIR / filename

        (
            result,
            label_counts,
            manifest_record,
        ) = inspect_file(path)

        summaries.append(
            result["summary"]
        )

        details.append(
            result["details"]
        )

        label_tables.append(
            label_counts
        )

        manifest_records.append(
            manifest_record
        )

        schema = (
            result["details"][
                "normalized_raw_header"
            ]
        )

        if reference_schema is None:
            reference_schema = schema

        elif schema != reference_schema:
            schemas_match = False

            print(
                "  WARNING: schema differs "
                "from first file: "
                f"{filename}"
            )

    summary_df = pd.DataFrame(
        summaries
    )

    label_df = pd.concat(
        label_tables,
        ignore_index=True,
    )

    overall_labels = (
        label_df
        .groupby(
            "label",
            dropna=False,
        )["count"]
        .sum()
        .sort_values(
            ascending=False
        )
        .rename_axis("label")
        .reset_index(
            name="count"
        )
    )

    total_rows = int(
        summary_df["rows"].sum()
    )

    overall_labels[
        "percentage"
    ] = (
        overall_labels["count"]
        / total_rows
        * 100
    )

    total_benign = int(
        summary_df[
            "benign_rows"
        ].sum()
    )

    total_attack = int(
        summary_df[
            "attack_rows"
        ].sum()
    )

    total_invalid_rows = int(
        summary_df[
            "invalid_rows"
        ].sum()
    )

    total_duplicate_rows = int(
        summary_df[
            "duplicate_rows"
        ].sum()
    )

    overall_report = {
        "file_count": (
            len(EXPECTED_FILES)
        ),
        "schemas_match": (
            schemas_match
        ),
        "total_rows": (
            total_rows
        ),
        "total_benign_rows": (
            total_benign
        ),
        "total_attack_rows": (
            total_attack
        ),
        "overall_attack_share": (
            total_attack / total_rows
            if total_rows
            else 0.0
        ),
        "total_invalid_rows": (
            total_invalid_rows
        ),
        "sum_within_file_duplicate_rows": (
            total_duplicate_rows
        ),
        "files": details,
    }

    # ---------------------------------------------------------
    # Reproducible diagnostic outputs
    # ---------------------------------------------------------
    summary_df.to_csv(
        OUTPUT_DIR
        / "file_summary.csv",
        index=False,
    )

    label_df.to_csv(
        OUTPUT_DIR
        / "labels_by_file.csv",
        index=False,
    )

    overall_labels.to_csv(
        OUTPUT_DIR
        / "overall_label_distribution.csv",
        index=False,
    )

    with (
        OUTPUT_DIR
        / "audit_details.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            overall_report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # Permanent raw-data provenance manifest
    #
    # This file IS intended to be committed to Git.
    # It contains no dataset rows, only metadata and SHA-256 hashes.
    # ---------------------------------------------------------
    permanent_manifest = {
        "dataset": "CICIDS2017",
        "dataset_representation": (
            "MachineLearningCSV working-day files"
        ),
        "file_order": (
            EXPECTED_FILES
        ),
        "file_count": (
            len(EXPECTED_FILES)
        ),
        "schemas_match": (
            schemas_match
        ),
        "total_rows": (
            total_rows
        ),
        "total_benign_rows": (
            total_benign
        ),
        "total_attack_rows": (
            total_attack
        ),
        "files": (
            manifest_records
        ),
    }

    with PERMANENT_MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            permanent_manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # Console summary
    # ---------------------------------------------------------
    print("\n" + "=" * 72)
    print("OVERALL DATASET")
    print("=" * 72)

    print(
        f"Files:              "
        f"{len(EXPECTED_FILES)}"
    )

    print(
        f"Schemas identical:  "
        f"{schemas_match}"
    )

    print(
        f"Total rows:         "
        f"{total_rows:,}"
    )

    print(
        f"BENIGN rows:        "
        f"{total_benign:,}"
    )

    print(
        f"Attack rows:        "
        f"{total_attack:,}"
    )

    attack_share_percent = (
        total_attack / total_rows * 100
        if total_rows
        else 0.0
    )

    print(
        f"Attack share:       "
        f"{attack_share_percent:.4f}%"
    )

    print(
        f"Invalid rows:       "
        f"{total_invalid_rows:,}"
    )

    print(
        "Within-file duplicate rows: "
        f"{total_duplicate_rows:,}"
    )

    print(
        "\nOverall label distribution:"
    )

    print(
        overall_labels.to_string(
            index=False,
            formatters={
                "percentage": (
                    lambda value:
                    f"{value:.6f}%"
                )
            },
        )
    )

    print(
        "\nDiagnostic outputs written to:"
    )
    print(OUTPUT_DIR)

    print(
        "\nPermanent raw-data manifest written to:"
    )
    print(
        PERMANENT_MANIFEST_PATH
    )


if __name__ == "__main__":
    main()