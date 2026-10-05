from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "cicids2017"
INTERIM_DATA_DIR = PROJECT_ROOT / "data" / "interim" / "cicids2017"


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


METADATA_COLUMNS = [
    "source_file",
    "source_order",
    "row_in_source",
]


LABEL_NORMALIZATION = {
    "Web Attack \uFFFD Brute Force": "Web Attack - Brute Force",
    "Web Attack \uFFFD XSS": "Web Attack - XSS",
    "Web Attack \uFFFD Sql Injection": "Web Attack - SQL Injection",
}


PRIMARY_DUPLICATE_COLUMN = "Fwd Header Length"
SECONDARY_DUPLICATE_COLUMN = "Fwd Header Length.1"


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove leading/trailing whitespace from CICIDS2017 column names.
    """
    df = df.copy()
    df.columns = [str(column).strip() for column in df.columns]

    return df


def validate_and_remove_duplicate_feature(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    CICIDS2017 contains two columns named 'Fwd Header Length'
    in the raw CSV header.

    pandas automatically renames the second occurrence to
    'Fwd Header Length.1'.

    We only remove the second column after verifying that both
    columns are exactly equal.
    """
    primary_exists = PRIMARY_DUPLICATE_COLUMN in df.columns
    secondary_exists = SECONDARY_DUPLICATE_COLUMN in df.columns

    if not primary_exists:
        raise ValueError(
            f"Expected column missing: {PRIMARY_DUPLICATE_COLUMN}"
        )

    if not secondary_exists:
        raise ValueError(
            "Expected duplicated CICIDS2017 feature was not found as "
            f"'{SECONDARY_DUPLICATE_COLUMN}'."
        )

    if not df[PRIMARY_DUPLICATE_COLUMN].equals(
        df[SECONDARY_DUPLICATE_COLUMN]
    ):
        raise ValueError(
            "The two 'Fwd Header Length' columns are not identical. "
            "Refusing to remove either column."
        )

    return df.drop(columns=[SECONDARY_DUPLICATE_COLUMN])


def normalize_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize known malformed CICIDS2017 Web Attack labels.

    This does not merge classes or create binary labels.
    """
    if "Label" not in df.columns:
        raise ValueError("'Label' column is missing.")

    if df["Label"].isna().any():
        raise ValueError(
            "Missing labels detected. Labels must not be imputed."
        )

    df = df.copy()

    df["Label"] = (
        df["Label"]
        .astype("string")
        .str.strip()
        .replace(LABEL_NORMALIZATION)
    )

    return df


def validate_feature_types(df: pd.DataFrame) -> None:
    """
    Verify that every model feature is numeric.

    Metadata columns do not exist yet at this stage.
    """
    feature_columns = [
        column
        for column in df.columns
        if column != "Label"
    ]

    non_numeric = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(df[column])
    ]

    if non_numeric:
        raise TypeError(
            "Non-numeric model features detected:\n"
            + "\n".join(f"  - {column}" for column in non_numeric)
        )


def replace_infinities_with_nan(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert positive and negative infinity to NaN.

    Missing values are intentionally NOT imputed here.
    Imputation must later be fitted only on historical training data.
    """
    df = df.copy()

    feature_columns = [
        column
        for column in df.columns
        if column != "Label"
    ]

    df.loc[:, feature_columns] = (
        df.loc[:, feature_columns]
        .replace([np.inf, -np.inf], np.nan)
    )

    return df


def add_stream_metadata(
    df: pd.DataFrame,
    source_file: str,
    source_order: int,
) -> pd.DataFrame:
    """
    Add metadata needed to reconstruct the pseudo-chronological stream.

    These columns MUST NOT be used as model features.
    """
    df = df.copy()

    df.insert(
        0,
        "row_in_source",
        np.arange(len(df), dtype=np.int64),
    )

    df.insert(
        0,
        "source_order",
        source_order,
    )

    df.insert(
        0,
        "source_file",
        source_file,
    )

    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """
    Return model feature names while excluding labels and stream metadata.
    """
    excluded = set(METADATA_COLUMNS + ["Label"])

    return [
        column
        for column in df.columns
        if column not in excluded
    ]


def preprocess_file(
    path: Path,
    source_order: int,
) -> tuple[pd.DataFrame, dict]:
    """
    Perform structural preprocessing only.

    No fitting, scaling, imputation, sampling, or feature selection
    happens here.
    """
    print(f"Preprocessing: {path.name}")

    df = pd.read_csv(
        path,
        low_memory=False,
    )

    original_rows = len(df)
    original_columns = len(df.columns)

    df = normalize_column_names(df)

    df = validate_and_remove_duplicate_feature(df)

    df = normalize_labels(df)

    validate_feature_types(df)

    df = replace_infinities_with_nan(df)

    missing_rows = int(
        df.drop(columns=["Label"])
        .isna()
        .any(axis=1)
        .sum()
    )

    missing_cells = int(
        df.drop(columns=["Label"])
        .isna()
        .sum()
        .sum()
    )

    duplicate_rows = int(
        df.duplicated(
            subset=[
                column
                for column in df.columns
                if column != "Label"
            ],
            keep="first",
        ).sum()
    )

    label_counts = {
        str(label): int(count)
        for label, count in (
            df["Label"]
            .value_counts(dropna=False)
            .items()
        )
    }

    df = add_stream_metadata(
        df=df,
        source_file=path.name,
        source_order=source_order,
    )

    feature_columns = get_feature_columns(df)

    report = {
        "source_file": path.name,
        "source_order": source_order,
        "original_rows": original_rows,
        "original_columns": original_columns,
        "rows_after_structural_preprocessing": len(df),
        "columns_after_structural_preprocessing": len(df.columns),
        "model_feature_count": len(feature_columns),
        "missing_feature_rows_after_inf_conversion": missing_rows,
        "missing_feature_cells_after_inf_conversion": missing_cells,
        "duplicate_feature_rows_retained": duplicate_rows,
        "labels": label_counts,
    }

    return df, report


def main() -> None:
    if not RAW_DATA_DIR.exists():
        raise FileNotFoundError(
            f"Raw CICIDS2017 directory not found:\n{RAW_DATA_DIR}"
        )

    INTERIM_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    reports = []
    reference_feature_columns = None

    print("=" * 72)
    print("CICIDS2017 STRUCTURAL PREPROCESSING")
    print("=" * 72)

    for source_order, filename in enumerate(EXPECTED_FILES):
        input_path = RAW_DATA_DIR / filename

        if not input_path.exists():
            raise FileNotFoundError(
                f"Expected file not found:\n{input_path}"
            )

        df, report = preprocess_file(
            path=input_path,
            source_order=source_order,
        )

        feature_columns = get_feature_columns(df)

        if reference_feature_columns is None:
            reference_feature_columns = feature_columns
        elif feature_columns != reference_feature_columns:
            raise ValueError(
                f"Feature schema mismatch after preprocessing: {filename}"
            )

        output_name = f"{input_path.stem}.csv.gz"
        output_path = INTERIM_DATA_DIR / output_name

        df.to_csv(
            output_path,
            index=False,
            compression="gzip",
        )

        reports.append(report)

        print(
            f"  rows retained:       {len(df):,}\n"
            f"  model features:      {len(feature_columns)}\n"
            f"  missing-value rows:  "
            f"{report['missing_feature_rows_after_inf_conversion']:,}\n"
            f"  output:              {output_path.name}"
        )

        del df

    manifest = {
        "dataset": "CICIDS2017",
        "processing_stage": "structural_preprocessing",
        "files_processed": len(reports),
        "label_normalization": LABEL_NORMALIZATION,
        "dropped_duplicate_feature": SECONDARY_DUPLICATE_COLUMN,
        "metadata_columns": METADATA_COLUMNS,
        "feature_count": len(reference_feature_columns or []),
        "feature_columns": reference_feature_columns or [],
        "files": reports,
    }

    manifest_path = (
        INTERIM_DATA_DIR
        / "preprocessing_manifest.json"
    )

    with manifest_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 72)
    print("STRUCTURAL PREPROCESSING COMPLETE")
    print("=" * 72)

    print(f"Files processed: {len(reports)}")
    print(
        f"Model features:  "
        f"{len(reference_feature_columns or [])}"
    )
    print(f"Manifest:        {manifest_path}")


if __name__ == "__main__":
    main()