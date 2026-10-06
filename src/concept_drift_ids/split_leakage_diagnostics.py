from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cicids2017"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "results"
    / "split_leakage_diagnostics"
)

PREPROCESSING_MANIFEST = (
    INTERIM_DIR
    / "preprocessing_manifest.json"
)


MONDAY = (
    "Monday-WorkingHours.pcap_ISCX.csv.gz"
)

TUESDAY = (
    "Tuesday-WorkingHours.pcap_ISCX.csv.gz"
)

WEDNESDAY = (
    "Wednesday-workingHours.pcap_ISCX.csv.gz"
)

THURSDAY_MORNING = (
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.gz"
)


CHUNK_SIZE = 100_000


# ---------------------------------------------------------
# Proposed scenario boundaries
# ---------------------------------------------------------

TRAIN_WEDNESDAY_START = 0
TRAIN_WEDNESDAY_END = 346_352

DEVELOPMENT_START = 346_352
DEVELOPMENT_END = 554_162

PRE_DRIFT_START = 554_162
PRE_DRIFT_END = 623_433

POST_ATTACK_START = 623_433
POST_ATTACK_END = 692_703

POST_BENIGN_REQUIRED = 65_697


PARTITION_ORDER = [
    "training",
    "development",
    "pre_drift",
    "post_attack",
    "post_benign",
]


COMPARISONS_TO_RUN = [
    ("training", "development"),
    ("training", "pre_drift"),
    ("training", "post_attack"),
    ("training", "post_benign"),
    ("development", "pre_drift"),
    ("development", "post_attack"),
    ("development", "post_benign"),
    ("pre_drift", "post_attack"),
    ("pre_drift", "post_benign"),
]


EXPECTED_PARTITION_SIZES = {
    "training": 1_322_179,
    "development": 207_810,
    "pre_drift": 69_260,
    "post_attack": 3_573,
    "post_benign": 65_697,
}


def load_feature_columns() -> list[str]:
    with PREPROCESSING_MANIFEST.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    feature_columns = (
        manifest.get(
            "feature_columns"
        )
    )

    if not feature_columns:
        raise ValueError(
            "feature_columns missing from "
            "preprocessing manifest."
        )

    if len(feature_columns) != 77:
        raise ValueError(
            "Expected 77 model features, "
            f"found {len(feature_columns)}."
        )

    return feature_columns


def deterministic_positions(
    total_rows: int,
    requested_rows: int,
) -> np.ndarray:
    """
    Choose evenly spaced positions deterministically.

    No random-number generator is used.
    """
    if requested_rows > total_rows:
        raise ValueError(
            f"Requested {requested_rows:,} rows "
            f"from only {total_rows:,} rows."
        )

    return (
        np.arange(
            requested_rows,
            dtype=np.int64,
        )
        * total_rows
        // requested_rows
    )


def select_chunk(
    chunk: pd.DataFrame,
    start_row: int | None = None,
    end_row: int | None = None,
    include_labels: set[str] | None = None,
    exclude_labels: set[str] | None = None,
) -> pd.DataFrame:
    """
    Apply pseudo-chronological and label restrictions to one chunk.
    """
    mask = np.ones(
        len(chunk),
        dtype=bool,
    )

    row_values = (
        chunk["row_in_source"]
        .to_numpy(
            copy=False
        )
    )

    if start_row is not None:
        mask = (
            mask
            & (
                row_values
                >= start_row
            )
        )

    if end_row is not None:
        mask = (
            mask
            & (
                row_values
                < end_row
            )
        )

    if include_labels is not None:
        mask = (
            mask
            & chunk["Label"]
            .isin(include_labels)
            .to_numpy(
                copy=False
            )
        )

    if exclude_labels is not None:
        mask = (
            mask
            & (
                ~chunk["Label"]
                .isin(exclude_labels)
                .to_numpy(
                    copy=False
                )
            )
        )

    return (
        chunk.loc[mask]
        .copy()
    )


def iter_source_slice(
    path: Path,
    columns: list[str],
    start_row: int | None = None,
    end_row: int | None = None,
    include_labels: set[str] | None = None,
    exclude_labels: set[str] | None = None,
):
    """
    Stream one requested source slice in bounded-memory chunks.
    """
    for chunk in pd.read_csv(
        path,
        usecols=columns,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        selected = select_chunk(
            chunk=chunk,
            start_row=start_row,
            end_row=end_row,
            include_labels=include_labels,
            exclude_labels=exclude_labels,
        )

        if not selected.empty:
            yield selected


def iter_partition_frames(
    partition_name: str,
    columns: list[str],
):
    """
    Yield DataFrames belonging to one proposed experimental partition.
    """
    if partition_name == "training":
        yield from iter_source_slice(
            path=INTERIM_DIR / MONDAY,
            columns=columns,
        )

        yield from iter_source_slice(
            path=INTERIM_DIR / TUESDAY,
            columns=columns,
        )

        yield from iter_source_slice(
            path=INTERIM_DIR / WEDNESDAY,
            columns=columns,
            start_row=(
                TRAIN_WEDNESDAY_START
            ),
            end_row=(
                TRAIN_WEDNESDAY_END
            ),
        )

        return

    if partition_name == "development":
        yield from iter_source_slice(
            path=INTERIM_DIR / WEDNESDAY,
            columns=columns,
            start_row=DEVELOPMENT_START,
            end_row=DEVELOPMENT_END,
        )

        return

    if partition_name == "pre_drift":
        yield from iter_source_slice(
            path=INTERIM_DIR / WEDNESDAY,
            columns=columns,
            start_row=PRE_DRIFT_START,
            end_row=PRE_DRIFT_END,
            exclude_labels={
                "Heartbleed"
            },
        )

        return

    if partition_name == "post_attack":
        yield from iter_source_slice(
            path=INTERIM_DIR / WEDNESDAY,
            columns=columns,
            start_row=POST_ATTACK_START,
            end_row=POST_ATTACK_END,
            include_labels={
                "DoS GoldenEye"
            },
        )

        return

    if partition_name == "post_benign":
        # Thursday morning is small enough that selecting the BENIGN
        # subset in memory is reasonable and makes the deterministic
        # subsampling rule completely explicit.
        thursday = pd.read_csv(
            INTERIM_DIR
            / THURSDAY_MORNING,
            usecols=columns,
            low_memory=False,
        )

        benign = (
            thursday.loc[
                thursday["Label"]
                == "BENIGN"
            ]
            .reset_index(
                drop=True
            )
        )

        if len(benign) != 168_186:
            raise ValueError(
                "Unexpected Thursday-morning "
                "BENIGN count: "
                f"{len(benign):,}"
            )

        positions = (
            deterministic_positions(
                total_rows=len(benign),
                requested_rows=(
                    POST_BENIGN_REQUIRED
                ),
            )
        )

        yield (
            benign.iloc[
                positions
            ]
            .copy()
        )

        return

    raise ValueError(
        f"Unknown partition: "
        f"{partition_name}"
    )


def hash_frame(
    df: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[
    np.ndarray,
    np.ndarray,
]:
    """
    Produce deterministic 64-bit fingerprints.

    IMPORTANT:
    These fingerprints are used only to narrow down candidate
    duplicate/overlap rows.

    Final claims of equality are checked using the actual feature
    values later in the script.
    """
    feature_hash = (
        pd.util.hash_pandas_object(
            df[feature_columns],
            index=False,
        )
        .to_numpy(
            dtype=np.uint64,
            copy=True,
        )
    )

    feature_label_hash = (
        pd.util.hash_pandas_object(
            df[
                feature_columns
                + ["Label"]
            ],
            index=False,
        )
        .to_numpy(
            dtype=np.uint64,
            copy=True,
        )
    )

    return (
        feature_hash,
        feature_label_hash,
    )


def build_hash_records(
    partition_name: str,
    feature_columns: list[str],
) -> pd.DataFrame:
    """
    First pass over a partition.

    Stores only fingerprints and labels, keeping memory use much
    smaller than retaining all 77 features.
    """
    columns = (
        [
            "source_file",
            "row_in_source",
            "Label",
        ]
        + feature_columns
    )

    parts = []

    for frame in iter_partition_frames(
        partition_name=partition_name,
        columns=columns,
    ):
        (
            feature_hash,
            feature_label_hash,
        ) = hash_frame(
            frame,
            feature_columns,
        )

        part = pd.DataFrame(
            {
                "feature_hash": (
                    feature_hash
                ),
                "feature_label_hash": (
                    feature_label_hash
                ),
                "label": (
                    frame["Label"]
                    .astype(str)
                    .to_numpy()
                ),
            }
        )

        parts.append(part)

    if not parts:
        raise ValueError(
            f"No rows found for "
            f"{partition_name}"
        )

    result = pd.concat(
        parts,
        ignore_index=True,
    )

    # Category dtype reduces memory for repeated label strings.
    result["label"] = (
        result["label"]
        .astype("category")
    )

    expected = (
        EXPECTED_PARTITION_SIZES[
            partition_name
        ]
    )

    if len(result) != expected:
        raise ValueError(
            f"{partition_name} expected "
            f"{expected:,} rows, found "
            f"{len(result):,}."
        )

    return result


def repeated_hashes(
    values: np.ndarray,
) -> np.ndarray:
    """
    Return fingerprint values appearing more than once.
    """
    unique_values, counts = (
        np.unique(
            values,
            return_counts=True,
        )
    )

    return unique_values[
        counts > 1
    ]


def identify_potential_conflict_hashes(
    partition_records: dict[
        str,
        pd.DataFrame,
    ],
) -> tuple[
    np.ndarray,
    pd.DataFrame,
]:
    """
    Find feature fingerprints associated with more than one label.

    These are only potential conflicts until actual feature values are
    compared.
    """
    parts = []

    for partition_name, records in (
        partition_records.items()
    ):
        part = records[
            [
                "feature_hash",
                "label",
            ]
        ].copy()

        part["partition"] = (
            partition_name
        )

        parts.append(part)

    combined = pd.concat(
        parts,
        ignore_index=True,
    )

    distinct_pairs = (
        combined[
            [
                "feature_hash",
                "label",
            ]
        ]
        .drop_duplicates()
    )

    label_counts = (
        distinct_pairs
        .groupby(
            "feature_hash",
            observed=True,
        )["label"]
        .nunique()
    )

    conflict_hashes = (
        label_counts[
            label_counts > 1
        ]
        .index
        .to_numpy(
            dtype=np.uint64
        )
    )

    potential_rows = (
        combined.loc[
            combined[
                "feature_hash"
            ].isin(
                conflict_hashes
            )
        ]
        .copy()
    )

    if potential_rows.empty:
        summary = pd.DataFrame(
            columns=[
                "feature_hash",
                "rows",
                "labels",
                "partitions",
            ]
        )

    else:
        summary_records = []

        for feature_hash, group in (
            potential_rows.groupby(
                "feature_hash",
                sort=False,
                observed=True,
            )
        ):
            labels = sorted(
                {
                    str(value)
                    for value
                    in group["label"]
                }
            )

            partitions = sorted(
                set(
                    group["partition"]
                    .astype(str)
                )
            )

            summary_records.append(
                {
                    "feature_hash": int(
                        feature_hash
                    ),
                    "rows": int(
                        len(group)
                    ),
                    "labels": " | ".join(
                        labels
                    ),
                    "partitions": " | ".join(
                        partitions
                    ),
                }
            )

        summary = pd.DataFrame(
            summary_records
        )

    return (
        conflict_hashes,
        summary,
    )


def build_verification_hash_set(
    partition_records: dict[
        str,
        pd.DataFrame,
    ],
    potential_conflict_hashes: np.ndarray,
) -> np.ndarray:
    """
    Build one union of fingerprints that need second-pass,
    value-level verification.

    Includes:
      - repeated patterns within any partition
      - patterns crossing any planned partition comparison
      - fingerprints associated with potentially conflicting labels
    """
    arrays = []

    if len(
        potential_conflict_hashes
    ):
        arrays.append(
            potential_conflict_hashes
        )

    # Repeated patterns within each partition.
    for records in (
        partition_records.values()
    ):
        arrays.append(
            repeated_hashes(
                records[
                    "feature_hash"
                ].to_numpy(
                    dtype=np.uint64,
                    copy=False,
                )
            )
        )

    # Cross-partition candidate overlaps.
    for (
        reference_name,
        candidate_name,
    ) in COMPARISONS_TO_RUN:
        reference_hashes = np.unique(
            partition_records[
                reference_name
            ]["feature_hash"]
            .to_numpy(
                dtype=np.uint64,
                copy=False,
            )
        )

        candidate_hashes = np.unique(
            partition_records[
                candidate_name
            ]["feature_hash"]
            .to_numpy(
                dtype=np.uint64,
                copy=False,
            )
        )

        intersection = (
            np.intersect1d(
                reference_hashes,
                candidate_hashes,
                assume_unique=True,
            )
        )

        arrays.append(
            intersection
        )

    non_empty = [
        array
        for array in arrays
        if len(array)
    ]

    if not non_empty:
        return np.empty(
            0,
            dtype=np.uint64,
        )

    return np.unique(
        np.concatenate(
            non_empty
        )
    )


def collect_verification_rows(
    partition_name: str,
    feature_columns: list[str],
    verification_hashes: np.ndarray,
) -> pd.DataFrame:
    """
    Second pass.

    Reload only rows whose fingerprints indicate that they might
    participate in duplicates, overlap, or label conflicts.

    Actual feature values are retained here for exact verification.
    """
    columns = (
        [
            "source_file",
            "row_in_source",
            "Label",
        ]
        + feature_columns
    )

    parts = []

    for frame in iter_partition_frames(
        partition_name=partition_name,
        columns=columns,
    ):
        (
            feature_hash,
            _,
        ) = hash_frame(
            frame,
            feature_columns,
        )

        mask = np.isin(
            feature_hash,
            verification_hashes,
            assume_unique=False,
        )

        if not mask.any():
            continue

        selected = (
            frame.loc[mask]
            .copy()
        )

        selected.insert(
            0,
            "feature_hash",
            feature_hash[mask],
        )

        selected.insert(
            0,
            "partition",
            partition_name,
        )

        parts.append(
            selected
        )

    if not parts:
        return pd.DataFrame(
            columns=(
                [
                    "partition",
                    "feature_hash",
                    "source_file",
                    "row_in_source",
                    "Label",
                ]
                + feature_columns
            )
        )

    return pd.concat(
        parts,
        ignore_index=True,
    )


def exact_partition_duplicate_summary(
    partition_name: str,
    hash_records: pd.DataFrame,
    verification_rows: pd.DataFrame,
    feature_columns: list[str],
) -> dict:
    """
    Calculate duplicate counts using actual feature values.

    Rows not present in verification_rows had unique fingerprints and
    therefore cannot be exact duplicates unless a fingerprinting error
    occurred in the opposite direction, which deterministic hashing
    does not create for equal values.
    """
    total_rows = len(
        hash_records
    )

    fingerprint_unique_features = int(
        hash_records[
            "feature_hash"
        ].nunique()
    )

    fingerprint_unique_full = int(
        hash_records[
            "feature_label_hash"
        ].nunique()
    )

    fingerprint_duplicate_features = (
        total_rows
        - fingerprint_unique_features
    )

    fingerprint_duplicate_full = (
        total_rows
        - fingerprint_unique_full
    )

    partition_verification = (
        verification_rows.loc[
            verification_rows[
                "partition"
            ]
            == partition_name
        ]
    )

    exact_duplicate_features = int(
        partition_verification
        .duplicated(
            subset=feature_columns,
            keep="first",
        )
        .sum()
    )

    exact_duplicate_full = int(
        partition_verification
        .duplicated(
            subset=(
                feature_columns
                + ["Label"]
            ),
            keep="first",
        )
        .sum()
    )

    return {
        "partition": (
            partition_name
        ),
        "rows": (
            total_rows
        ),
        "exact_unique_feature_patterns": (
            total_rows
            - exact_duplicate_features
        ),
        "exact_unique_feature_label_patterns": (
            total_rows
            - exact_duplicate_full
        ),
        "exact_duplicate_feature_rows": (
            exact_duplicate_features
        ),
        "exact_duplicate_feature_label_rows": (
            exact_duplicate_full
        ),
        "fingerprint_duplicate_feature_rows": (
            fingerprint_duplicate_features
        ),
        "fingerprint_duplicate_feature_label_rows": (
            fingerprint_duplicate_full
        ),
        "feature_hash_false_positive_duplicates": (
            fingerprint_duplicate_features
            - exact_duplicate_features
        ),
        "feature_label_hash_false_positive_duplicates": (
            fingerprint_duplicate_full
            - exact_duplicate_full
        ),
    }


def verify_exact_label_conflicts(
    verification_rows: pd.DataFrame,
    potential_conflict_hashes: np.ndarray,
    feature_columns: list[str],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Determine whether potentially conflicting fingerprints represent
    genuinely identical 77-feature vectors carrying different labels.
    """
    if not len(
        potential_conflict_hashes
    ):
        return (
            pd.DataFrame(),
            pd.DataFrame(),
        )

    candidates = (
        verification_rows.loc[
            verification_rows[
                "feature_hash"
            ].isin(
                potential_conflict_hashes
            )
        ]
        .copy()
    )

    if candidates.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
        )

    label_nunique = (
        candidates
        .groupby(
            feature_columns,
            dropna=False,
            sort=False,
        )["Label"]
        .transform(
            "nunique"
        )
    )

    exact_conflicts = (
        candidates.loc[
            label_nunique > 1
        ]
        .copy()
    )

    if exact_conflicts.empty:
        return (
            exact_conflicts,
            pd.DataFrame(),
        )

    exact_conflicts[
        "exact_conflict_group_id"
    ] = (
        exact_conflicts
        .groupby(
            feature_columns,
            dropna=False,
            sort=False,
        )
        .ngroup()
        + 1
    )

    group_records = []

    for group_id, group in (
        exact_conflicts.groupby(
            "exact_conflict_group_id",
            sort=True,
        )
    ):
        labels = sorted(
            set(
                group["Label"]
                .astype(str)
            )
        )

        partitions = sorted(
            set(
                group["partition"]
                .astype(str)
            )
        )

        source_files = sorted(
            set(
                group["source_file"]
                .astype(str)
            )
        )

        group_records.append(
            {
                "exact_conflict_group_id": int(
                    group_id
                ),
                "rows_involved": int(
                    len(group)
                ),
                "label_count": (
                    len(labels)
                ),
                "labels": (
                    " | ".join(
                        labels
                    )
                ),
                "partitions": (
                    " | ".join(
                        partitions
                    )
                ),
                "source_files": (
                    " | ".join(
                        source_files
                    )
                ),
            }
        )

    group_summary = pd.DataFrame(
        group_records
    )

    return (
        exact_conflicts,
        group_summary,
    )


def exact_overlap_for_pair(
    reference_name: str,
    candidate_name: str,
    partition_records: dict[
        str,
        pd.DataFrame,
    ],
    verification_rows: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[
    dict,
    pd.DataFrame,
]:
    """
    Compare two partitions.

    Hashes first identify candidate overlaps.
    Actual feature values then determine true overlap.
    """
    reference_records = (
        partition_records[
            reference_name
        ]
    )

    candidate_records = (
        partition_records[
            candidate_name
        ]
    )

    reference_feature_hashes = np.unique(
        reference_records[
            "feature_hash"
        ].to_numpy(
            dtype=np.uint64,
            copy=False,
        )
    )

    reference_full_hashes = np.unique(
        reference_records[
            "feature_label_hash"
        ].to_numpy(
            dtype=np.uint64,
            copy=False,
        )
    )

    candidate_feature_hashes = (
        candidate_records[
            "feature_hash"
        ].to_numpy(
            dtype=np.uint64,
            copy=False,
        )
    )

    candidate_full_hashes = (
        candidate_records[
            "feature_label_hash"
        ].to_numpy(
            dtype=np.uint64,
            copy=False,
        )
    )

    fingerprint_feature_mask = (
        np.isin(
            candidate_feature_hashes,
            reference_feature_hashes,
            assume_unique=False,
        )
    )

    fingerprint_full_mask = (
        np.isin(
            candidate_full_hashes,
            reference_full_hashes,
            assume_unique=False,
        )
    )

    fingerprint_feature_rows = int(
        fingerprint_feature_mask.sum()
    )

    fingerprint_full_rows = int(
        fingerprint_full_mask.sum()
    )

    intersecting_feature_hashes = (
        np.intersect1d(
            reference_feature_hashes,
            np.unique(
                candidate_feature_hashes
            ),
            assume_unique=True,
        )
    )

    reference_rows = (
        verification_rows.loc[
            (
                verification_rows[
                    "partition"
                ]
                == reference_name
            )
            & (
                verification_rows[
                    "feature_hash"
                ].isin(
                    intersecting_feature_hashes
                )
            )
        ]
        .copy()
    )

    candidate_rows = (
        verification_rows.loc[
            (
                verification_rows[
                    "partition"
                ]
                == candidate_name
            )
            & (
                verification_rows[
                    "feature_hash"
                ].isin(
                    intersecting_feature_hashes
                )
            )
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    if (
        len(candidate_rows)
        != fingerprint_feature_rows
    ):
        raise RuntimeError(
            "Candidate verification-row count "
            "does not match fingerprint candidate count "
            f"for {reference_name} -> {candidate_name}: "
            f"{len(candidate_rows):,} vs "
            f"{fingerprint_feature_rows:,}"
        )

    candidate_rows[
        "_candidate_id"
    ] = np.arange(
        len(candidate_rows),
        dtype=np.int64,
    )

    # ---------------------------------------------------------
    # Exact feature-only overlap
    # ---------------------------------------------------------
    reference_unique_features = (
        reference_rows[
            feature_columns
        ]
        .drop_duplicates()
        .copy()
    )

    reference_unique_features[
        "_feature_match"
    ] = True

    feature_merge = (
        candidate_rows[
            ["_candidate_id"]
            + feature_columns
        ]
        .merge(
            reference_unique_features,
            how="left",
            on=feature_columns,
            sort=False,
        )
    )

    exact_feature_match = (
        feature_merge[
            "_feature_match"
        ]
        .fillna(False)
        .to_numpy(
            dtype=bool,
        )
    )

    # ---------------------------------------------------------
    # Exact feature + label overlap
    # ---------------------------------------------------------
    reference_unique_full = (
        reference_rows[
            feature_columns
            + ["Label"]
        ]
        .drop_duplicates()
        .copy()
    )

    reference_unique_full[
        "_full_match"
    ] = True

    full_merge = (
        candidate_rows[
            ["_candidate_id"]
            + feature_columns
            + ["Label"]
        ]
        .merge(
            reference_unique_full,
            how="left",
            on=(
                feature_columns
                + ["Label"]
            ),
            sort=False,
        )
    )

    exact_full_match = (
        full_merge[
            "_full_match"
        ]
        .fillna(False)
        .to_numpy(
            dtype=bool,
        )
    )

    if (
        len(exact_feature_match)
        != len(candidate_rows)
    ):
        raise RuntimeError(
            "Unexpected feature-merge row "
            "multiplication."
        )

    if (
        len(exact_full_match)
        != len(candidate_rows)
    ):
        raise RuntimeError(
            "Unexpected full-merge row "
            "multiplication."
        )

    candidate_rows[
        "_exact_feature_match"
    ] = exact_feature_match

    candidate_rows[
        "_exact_full_match"
    ] = exact_full_match

    exact_feature_rows = int(
        exact_feature_match.sum()
    )

    exact_full_rows = int(
        exact_full_match.sum()
    )

    candidate_total = len(
        candidate_records
    )

    summary = {
        "reference_partition": (
            reference_name
        ),
        "candidate_partition": (
            candidate_name
        ),
        "candidate_rows": (
            candidate_total
        ),
        "fingerprint_feature_overlap_rows": (
            fingerprint_feature_rows
        ),
        "exact_feature_overlap_rows": (
            exact_feature_rows
        ),
        "exact_feature_overlap_rate": (
            exact_feature_rows
            / candidate_total
            if candidate_total
            else 0.0
        ),
        "feature_hash_false_positive_rows": (
            fingerprint_feature_rows
            - exact_feature_rows
        ),
        "fingerprint_feature_label_overlap_rows": (
            fingerprint_full_rows
        ),
        "exact_feature_label_overlap_rows": (
            exact_full_rows
        ),
        "exact_feature_label_overlap_rate": (
            exact_full_rows
            / candidate_total
            if candidate_total
            else 0.0
        ),
        "feature_label_hash_false_positive_rows": (
            fingerprint_full_rows
            - exact_full_rows
        ),
    }

    # ---------------------------------------------------------
    # Breakdown by candidate label
    # ---------------------------------------------------------
    candidate_label_totals = (
        candidate_records[
            "label"
        ]
        .astype(str)
        .value_counts()
    )

    label_records = []

    for label, total in (
        candidate_label_totals.items()
    ):
        label_rows = (
            candidate_rows.loc[
                candidate_rows[
                    "Label"
                ].astype(str)
                == str(label)
            ]
        )

        exact_feature_label_rows = int(
            label_rows[
                "_exact_feature_match"
            ].sum()
        )

        exact_full_label_rows = int(
            label_rows[
                "_exact_full_match"
            ].sum()
        )

        label_records.append(
            {
                "reference_partition": (
                    reference_name
                ),
                "candidate_partition": (
                    candidate_name
                ),
                "label": (
                    str(label)
                ),
                "candidate_label_rows": int(
                    total
                ),
                "exact_feature_overlap_rows": (
                    exact_feature_label_rows
                ),
                "exact_feature_overlap_rate_within_label": (
                    exact_feature_label_rows
                    / int(total)
                    if total
                    else 0.0
                ),
                "exact_feature_label_overlap_rows": (
                    exact_full_label_rows
                ),
                "exact_feature_label_overlap_rate_within_label": (
                    exact_full_label_rows
                    / int(total)
                    if total
                    else 0.0
                ),
            }
        )

    label_summary = pd.DataFrame(
        label_records
    )

    return (
        summary,
        label_summary,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_columns = (
        load_feature_columns()
    )

    print("=" * 72)
    print(
        "CICIDS2017 SPLIT LEAKAGE "
        "AND LABEL-INTEGRITY DIAGNOSTICS"
    )
    print("=" * 72)

    # ---------------------------------------------------------
    # Pass 1: compact fingerprint records
    # ---------------------------------------------------------
    partition_records: dict[
        str,
        pd.DataFrame,
    ] = {}

    for partition_name in (
        PARTITION_ORDER
    ):
        print(
            "Fingerprinting partition: "
            f"{partition_name}"
        )

        partition_records[
            partition_name
        ] = build_hash_records(
            partition_name=partition_name,
            feature_columns=feature_columns,
        )

    # ---------------------------------------------------------
    # Potential same-feature / different-label cases
    # ---------------------------------------------------------
    (
        potential_conflict_hashes,
        potential_conflict_summary,
    ) = identify_potential_conflict_hashes(
        partition_records
    )

    potential_conflict_summary.to_csv(
        OUTPUT_DIR
        / "potential_label_conflicts.csv",
        index=False,
    )

    print(
        "\nPotential conflicting "
        "feature fingerprints: "
        f"{len(potential_conflict_hashes):,}"
    )

    # ---------------------------------------------------------
    # Determine which feature values require exact verification
    # ---------------------------------------------------------
    verification_hashes = (
        build_verification_hash_set(
            partition_records=(
                partition_records
            ),
            potential_conflict_hashes=(
                potential_conflict_hashes
            ),
        )
    )

    print(
        "Feature fingerprints requiring "
        "exact value verification: "
        f"{len(verification_hashes):,}"
    )

    # ---------------------------------------------------------
    # Pass 2: retrieve actual 77-feature values only where needed
    # ---------------------------------------------------------
    verification_parts = []

    for partition_name in (
        PARTITION_ORDER
    ):
        print(
            "Collecting verification rows: "
            f"{partition_name}"
        )

        part = (
            collect_verification_rows(
                partition_name=(
                    partition_name
                ),
                feature_columns=(
                    feature_columns
                ),
                verification_hashes=(
                    verification_hashes
                ),
            )
        )

        if not part.empty:
            verification_parts.append(
                part
            )

    if verification_parts:
        verification_rows = (
            pd.concat(
                verification_parts,
                ignore_index=True,
            )
        )

    else:
        verification_rows = (
            pd.DataFrame()
        )

    # ---------------------------------------------------------
    # Exact duplicate counts within partitions
    # ---------------------------------------------------------
    partition_summaries = []

    for partition_name in (
        PARTITION_ORDER
    ):
        partition_summaries.append(
            exact_partition_duplicate_summary(
                partition_name=(
                    partition_name
                ),
                hash_records=(
                    partition_records[
                        partition_name
                    ]
                ),
                verification_rows=(
                    verification_rows
                ),
                feature_columns=(
                    feature_columns
                ),
            )
        )

    partition_df = pd.DataFrame(
        partition_summaries
    )

    partition_df.to_csv(
        OUTPUT_DIR
        / "partition_duplicate_summary.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # Exact label conflict verification
    # ---------------------------------------------------------
    (
        exact_conflict_rows,
        exact_conflict_groups,
    ) = verify_exact_label_conflicts(
        verification_rows=(
            verification_rows
        ),
        potential_conflict_hashes=(
            potential_conflict_hashes
        ),
        feature_columns=(
            feature_columns
        ),
    )

    exact_conflict_rows.to_csv(
        OUTPUT_DIR
        / "exact_label_conflicts.csv",
        index=False,
    )

    exact_conflict_groups.to_csv(
        OUTPUT_DIR
        / "exact_label_conflict_groups.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # Exact cross-partition overlap verification
    # ---------------------------------------------------------
    overlap_summaries = []
    overlap_by_label_parts = []

    for (
        reference_name,
        candidate_name,
    ) in COMPARISONS_TO_RUN:
        print(
            "Exact overlap verification: "
            f"{reference_name} -> "
            f"{candidate_name}"
        )

        (
            summary,
            by_label,
        ) = exact_overlap_for_pair(
            reference_name=(
                reference_name
            ),
            candidate_name=(
                candidate_name
            ),
            partition_records=(
                partition_records
            ),
            verification_rows=(
                verification_rows
            ),
            feature_columns=(
                feature_columns
            ),
        )

        overlap_summaries.append(
            summary
        )

        overlap_by_label_parts.append(
            by_label
        )

    overlap_df = pd.DataFrame(
        overlap_summaries
    )

    overlap_by_label_df = (
        pd.concat(
            overlap_by_label_parts,
            ignore_index=True,
        )
    )

    overlap_df.to_csv(
        OUTPUT_DIR
        / "cross_partition_overlap.csv",
        index=False,
    )

    overlap_by_label_df.to_csv(
        OUTPUT_DIR
        / "cross_partition_overlap_by_label.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # Compact JSON summary
    # ---------------------------------------------------------
    exact_conflicting_patterns = (
        len(exact_conflict_groups)
    )

    exact_conflicting_rows = (
        len(exact_conflict_rows)
    )

    report = {
        "feature_count": (
            len(feature_columns)
        ),
        "fingerprint_method": (
            "pandas.util.hash_pandas_object "
            "uint64 fingerprint used only as "
            "candidate prefilter"
        ),
        "exact_verification": (
            "Candidate duplicates, cross-partition "
            "overlap, and label conflicts were "
            "verified using actual 77-feature values."
        ),
        "potential_conflicting_feature_fingerprints": (
            int(
                len(
                    potential_conflict_hashes
                )
            )
        ),
        "exact_conflicting_feature_patterns": (
            int(
                exact_conflicting_patterns
            )
        ),
        "exact_conflicting_rows": (
            int(
                exact_conflicting_rows
            )
        ),
        "partitions": (
            partition_summaries
        ),
        "cross_partition_overlap": (
            overlap_summaries
        ),
    }

    with (
        OUTPUT_DIR
        / "split_leakage_summary.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # Console output
    # ---------------------------------------------------------
    print("\n" + "=" * 72)
    print("PARTITION DUPLICATES — EXACTLY VERIFIED")
    print("=" * 72)

    display_partition_columns = [
        "partition",
        "rows",
        "exact_unique_feature_patterns",
        "exact_unique_feature_label_patterns",
        "exact_duplicate_feature_rows",
        "exact_duplicate_feature_label_rows",
        "feature_hash_false_positive_duplicates",
        "feature_label_hash_false_positive_duplicates",
    ]

    print(
        partition_df[
            display_partition_columns
        ].to_string(
            index=False
        )
    )

    print("\n" + "=" * 72)
    print("LABEL CONFLICT VERIFICATION")
    print("=" * 72)

    print(
        "Potential conflicting fingerprints: "
        f"{len(potential_conflict_hashes):,}"
    )

    print(
        "Exact conflicting feature patterns: "
        f"{exact_conflicting_patterns:,}"
    )

    print(
        "Rows involved in exact conflicts: "
        f"{exact_conflicting_rows:,}"
    )

    if not exact_conflict_groups.empty:
        print(
            "\nExact conflict groups:"
        )

        print(
            exact_conflict_groups.to_string(
                index=False
            )
        )

    print("\n" + "=" * 72)
    print("CROSS-PARTITION OVERLAP — EXACTLY VERIFIED")
    print("=" * 72)

    display_overlap_columns = [
        "reference_partition",
        "candidate_partition",
        "candidate_rows",
        "exact_feature_overlap_rows",
        "exact_feature_overlap_rate",
        "exact_feature_label_overlap_rows",
        "exact_feature_label_overlap_rate",
        "feature_hash_false_positive_rows",
        "feature_label_hash_false_positive_rows",
    ]

    print(
        overlap_df[
            display_overlap_columns
        ].to_string(
            index=False,
            formatters={
                "exact_feature_overlap_rate": (
                    lambda value:
                    f"{value:.6%}"
                ),
                "exact_feature_label_overlap_rate": (
                    lambda value:
                    f"{value:.6%}"
                ),
            },
        )
    )

    print("\n" + "=" * 72)
    print("CROSS-PARTITION OVERLAP BY LABEL")
    print("=" * 72)

    print(
        overlap_by_label_df.to_string(
            index=False,
            formatters={
                "exact_feature_overlap_rate_within_label": (
                    lambda value:
                    f"{value:.6%}"
                ),
                "exact_feature_label_overlap_rate_within_label": (
                    lambda value:
                    f"{value:.6%}"
                ),
            },
        )
    )

    print(
        "\nOutputs written to:"
    )

    print(
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()