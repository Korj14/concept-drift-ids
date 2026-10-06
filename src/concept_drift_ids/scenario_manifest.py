from __future__ import annotations

import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "cicids2017"
RESULTS_DIR = PROJECT_ROOT / "results" / "split_leakage_diagnostics"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

RAW_MANIFEST_PATH = MANIFEST_DIR / "cicids2017_raw_manifest.json"
PREPROCESSING_MANIFEST_PATH = INTERIM_DIR / "preprocessing_manifest.json"
CONFLICT_FILE_PATH = RESULTS_DIR / "exact_label_conflicts.csv"
REQUIREMENTS_LOCK_PATH = PROJECT_ROOT / "requirements-lock.txt"
OUTPUT_MANIFEST_PATH = MANIFEST_DIR / "sudden_benign_v1.json"


MONDAY = "Monday-WorkingHours.pcap_ISCX.csv.gz"
TUESDAY = "Tuesday-WorkingHours.pcap_ISCX.csv.gz"
WEDNESDAY = "Wednesday-workingHours.pcap_ISCX.csv.gz"
THURSDAY_MORNING = "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.gz"

MONDAY_SOURCE = "Monday-WorkingHours.pcap_ISCX.csv"
TUESDAY_SOURCE = "Tuesday-WorkingHours.pcap_ISCX.csv"
WEDNESDAY_SOURCE = "Wednesday-workingHours.pcap_ISCX.csv"
THURSDAY_MORNING_SOURCE = (
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"
)

EXPECTED_RAW_FILE_ORDER = [
    "Monday-WorkingHours.pcap_ISCX.csv",
    "Tuesday-WorkingHours.pcap_ISCX.csv",
    "Wednesday-workingHours.pcap_ISCX.csv",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
]

# Canonical JSON hash of the verified Stage-1 raw provenance manifest.
# Canonicalization makes this insensitive to whitespace/key formatting.
EXPECTED_RAW_MANIFEST_CANONICAL_SHA256 = (
    "ef1f58af1192091fdf1037edd3a2af6770dad6f0f731ac61cceb007c0cafd8ea"
)

EXPECTED_PYTHON_VERSION = "3.11.9"
EXPECTED_FEATURE_COUNT = 77

EXPECTED_SOURCE_ROWS = {
    MONDAY_SOURCE: 529_918,
    TUESDAY_SOURCE: 445_909,
    WEDNESDAY_SOURCE: 692_703,
    THURSDAY_MORNING_SOURCE: 170_366,
}


# ---------------------------------------------------------------------
# Frozen scenario boundaries
# ---------------------------------------------------------------------

TRAIN_WEDNESDAY_START = 0
TRAIN_WEDNESDAY_END = 346_352

DEVELOPMENT_START = 346_352
DEVELOPMENT_END = 554_162

PRE_DRIFT_START = 554_162
PRE_DRIFT_END = 623_433

POST_DRIFT_TEMPLATE_START = 623_433
POST_DRIFT_TEMPLATE_END = 692_703

POST_BENIGN_REQUIRED = 65_697


EXPECTED_TRAIN_LABELS = {
    "BENIGN": 1_064_858,
    "DoS GoldenEye": 1_118,
    "DoS Hulk": 231_073,
    "DoS Slowhttptest": 5_499,
    "DoS slowloris": 5_796,
    "FTP-Patator": 7_938,
    "SSH-Patator": 5_897,
}

EXPECTED_DEVELOPMENT_LABELS = {
    "BENIGN": 205_797,
    "DoS GoldenEye": 2_013,
}

EXPECTED_PRE_DRIFT_LABELS = {
    "BENIGN": 65_671,
    "DoS GoldenEye": 3_589,
}

EXPECTED_POST_DRIFT_LABELS = {
    "BENIGN": 65_697,
    "DoS GoldenEye": 3_573,
}


EXPECTED_CONFLICT_DIAGNOSTICS = {
    "total_conflict_patterns": 78,
    "total_conflict_rows": 4_877,
    "training_internal_conflict_patterns": 41,
    "training_internal_conflict_rows": 4_322,
    "training_internal_conflict_label_counts": {
        "BENIGN": 46,
        "DoS Hulk": 4_276,
    },
    "future_only_conflict_patterns": 37,
    "future_only_training_rows": 513,
    "future_only_future_rows": 37,
    "future_only_future_partition_label_counts": {
        "development|BENIGN": 34,
        "post_benign|BENIGN": 3,
    },
}


# Independently verified from the uploaded Stage-1 source files.
EXPECTED_POST_BENIGN_SOURCE_ROW_ID_SHA256 = (
    "2ab5636a81923eae27faa0eac8de4dd8b55af9fb991bf0ddfdf5419e69c017c9"
)

EXPECTED_POST_BENIGN_TEMPLATE_SLOT_SHA256 = (
    "e393262d5ba7f02dd167aee8575e4980fa108b9471cef8034bb069a1340f5527"
)

EXPECTED_POST_BENIGN_MAPPING_SHA256 = (
    "027112a593a9e6c28720e8393590110f00e8337680f88965fee1d3dc479462ad"
)


def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def sha256_normalized_text(
    path: Path,
) -> str:
    """
    Hash text content in a portable canonical form.

    Accept UTF-8 (with or without BOM) and BOM-marked UTF-16, then
    normalize line endings to LF and hash the canonical UTF-8 bytes.

    This keeps the semantic lock-file hash stable across common Windows
    text encodings without changing any dependency versions.
    """
    raw = path.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")

    elif raw.startswith(
        (
            b"\xff\xfe",
            b"\xfe\xff",
        )
    ):
        text = raw.decode("utf-16")

    else:
        text = raw.decode("utf-8")

    normalized = (
        text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def sha256_conflict_projection(
    path: Path,
) -> str:
    """
    Hash only the conflict fields used by this scenario,
    independent of CSV formatting.
    """
    frame = pd.read_csv(
        path,
        usecols=[
            "partition",
            "Label",
            "exact_conflict_group_id",
        ],
        low_memory=False,
    )

    digest = hashlib.sha256()

    for row in frame.itertuples(
        index=False,
        name=None,
    ):
        partition, label, group_id = row

        digest.update(
            (
                f"{partition}\t"
                f"{label}\t"
                f"{int(group_id)}\n"
            ).encode("utf-8")
        )

    return digest.hexdigest()


def sha256_canonical_json(
    path: Path,
) -> str:
    """
    Hash JSON semantically, independent of whitespace/key formatting.
    """
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(
        canonical
    ).hexdigest()


def sha256_int64_array(
    values: np.ndarray,
) -> str:
    """
    Hash integers using a platform-independent little-endian int64 form.
    """
    canonical = np.asarray(
        values,
        dtype="<i8",
    )

    return hashlib.sha256(
        canonical.tobytes()
    ).hexdigest()


def sha256_int64_pairs(
    left: np.ndarray,
    right: np.ndarray,
) -> str:
    if len(left) != len(right):
        raise ValueError(
            "Pair arrays must have the same length."
        )

    canonical = (
        np.column_stack(
            (
                left,
                right,
            )
        )
        .astype(
            "<i8",
            copy=False,
        )
    )

    return hashlib.sha256(
        canonical.tobytes()
    ).hexdigest()


def require_file(
    path: Path,
) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found:\n{path}"
        )


def sorted_label_counts(
    frame: pd.DataFrame,
) -> dict[str, int]:
    counts = (
        frame["Label"]
        .value_counts(
            dropna=False
        )
        .to_dict()
    )

    return {
        str(label): int(count)
        for label, count
        in sorted(
            counts.items(),
            key=lambda item: str(item[0]),
        )
    }


def merge_label_counts(
    *count_dicts: dict[str, int],
) -> dict[str, int]:
    combined = Counter()

    for counts in count_dicts:
        combined.update(counts)

    return {
        label: int(count)
        for label, count
        in sorted(
            combined.items()
        )
    }


def assert_equal(
    actual,
    expected,
    description: str,
) -> None:
    if actual != expected:
        raise AssertionError(
            f"{description} mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


def validate_environment() -> None:
    actual_python = platform.python_version()

    if actual_python != EXPECTED_PYTHON_VERSION:
        raise RuntimeError(
            "Unexpected Python version.\n"
            f"Expected: {EXPECTED_PYTHON_VERSION}\n"
            f"Actual:   {actual_python}"
        )


def validate_raw_manifest() -> dict:
    require_file(
        RAW_MANIFEST_PATH
    )

    canonical_sha256 = sha256_canonical_json(
        RAW_MANIFEST_PATH
    )

    assert_equal(
        canonical_sha256,
        EXPECTED_RAW_MANIFEST_CANONICAL_SHA256,
        "Raw-manifest canonical SHA-256",
    )

    with RAW_MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    assert_equal(
        manifest.get("dataset"),
        "CICIDS2017",
        "Raw-manifest dataset",
    )

    assert_equal(
        manifest.get("file_count"),
        8,
        "Raw-manifest file count",
    )

    assert_equal(
        manifest.get("schemas_match"),
        True,
        "Raw schema consistency",
    )

    assert_equal(
        manifest.get("total_rows"),
        2_830_743,
        "Raw total row count",
    )

    assert_equal(
        manifest.get(
            "total_benign_rows"
        ),
        2_273_097,
        "Raw BENIGN row count",
    )

    assert_equal(
        manifest.get(
            "total_attack_rows"
        ),
        557_646,
        "Raw attack row count",
    )

    assert_equal(
        manifest.get(
            "file_order"
        ),
        EXPECTED_RAW_FILE_ORDER,
        "Raw file order",
    )

    files = manifest.get(
        "files",
        [],
    )

    if len(files) != 8:
        raise AssertionError(
            "Raw manifest does not contain "
            "exactly eight file records."
        )

    hashes: list[str] = []

    for record in files:
        source_file = record.get(
            "source_file"
        )

        if (
            record.get("raw_columns")
            != 79
        ):
            raise AssertionError(
                "Unexpected raw column count "
                f"for {source_file}"
            )

        sha256 = record.get(
            "sha256",
            "",
        )

        if len(sha256) != 64:
            raise AssertionError(
                "Invalid SHA-256 value for "
                f"{source_file}"
            )

        if (
            sum(
                record.get(
                    "raw_label_counts",
                    {},
                ).values()
            )
            != record.get("rows")
        ):
            raise AssertionError(
                "Label counts do not sum to "
                "row count for "
                f"{source_file}"
            )

        hashes.append(
            sha256
        )

    if len(set(hashes)) != 8:
        raise AssertionError(
            "Raw-file SHA-256 values are not unique."
        )

    return manifest


def load_preprocessing_manifest() -> dict:
    require_file(
        PREPROCESSING_MANIFEST_PATH
    )

    with PREPROCESSING_MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    assert_equal(
        manifest.get(
            "feature_count"
        ),
        EXPECTED_FEATURE_COUNT,
        "Preprocessed feature count",
    )

    feature_columns = manifest.get(
        "feature_columns",
        [],
    )

    if (
        len(feature_columns)
        != EXPECTED_FEATURE_COUNT
    ):
        raise AssertionError(
            "Preprocessing manifest does not "
            "contain exactly 77 feature names."
        )

    if (
        len(set(feature_columns))
        != EXPECTED_FEATURE_COUNT
    ):
        raise AssertionError(
            "Preprocessing manifest contains "
            "duplicate feature names."
        )

    forbidden = {
        "Label",
        "source_file",
        "source_order",
        "row_in_source",
    }

    leaked = forbidden.intersection(
        feature_columns
    )

    if leaked:
        raise AssertionError(
            "Metadata/target columns leaked into "
            "feature_columns: "
            f"{sorted(leaked)}"
        )

    return manifest


def read_metadata(
    filename: str,
    *,
    expected_source_order: int,
    expected_source_file: str,
    expected_rows: int,
) -> pd.DataFrame:
    path = (
        INTERIM_DIR
        / filename
    )

    require_file(
        path
    )

    frame = pd.read_csv(
        path,
        usecols=[
            "source_file",
            "source_order",
            "row_in_source",
            "Label",
        ],
        low_memory=False,
    )

    assert_equal(
        len(frame),
        expected_rows,
        f"Row count for {filename}",
    )

    source_orders = (
        frame["source_order"]
        .unique()
    )

    if (
        len(source_orders) != 1
        or int(source_orders[0])
        != expected_source_order
    ):
        raise AssertionError(
            f"Unexpected source_order in "
            f"{filename}: {source_orders}"
        )

    source_files = (
        frame["source_file"]
        .astype(str)
        .unique()
    )

    if (
        len(source_files) != 1
        or source_files[0]
        != expected_source_file
    ):
        raise AssertionError(
            f"Unexpected source_file in "
            f"{filename}: {source_files}"
        )

    expected_row_ids = np.arange(
        len(frame),
        dtype=np.int64,
    )

    actual_row_ids = (
        frame["row_in_source"]
        .to_numpy(
            dtype=np.int64,
            copy=False,
        )
    )

    if not np.array_equal(
        expected_row_ids,
        actual_row_ids,
    ):
        raise AssertionError(
            "row_in_source is not contiguous "
            f"for {filename}."
        )

    if frame["Label"].isna().any():
        raise AssertionError(
            f"Missing labels in {filename}."
        )

    return frame


def deterministic_positions(
    total_rows: int,
    requested_rows: int,
) -> np.ndarray:
    """
    Evenly select eligible rows while preserving order and without randomness.

    position[k] = floor(k * total_rows / requested_rows)
    """
    if requested_rows <= 0:
        raise ValueError(
            "requested_rows must be positive."
        )

    if requested_rows > total_rows:
        raise ValueError(
            f"Cannot select {requested_rows:,} "
            f"rows from {total_rows:,} rows."
        )

    positions = (
        np.arange(
            requested_rows,
            dtype=np.int64,
        )
        * total_rows
        // requested_rows
    )

    if (
        len(
            np.unique(
                positions
            )
        )
        != requested_rows
    ):
        raise AssertionError(
            "Deterministic selection generated "
            "duplicate positions."
        )

    if (
        requested_rows > 1
        and not np.all(
            positions[:-1]
            < positions[1:]
        )
    ):
        raise AssertionError(
            "Deterministic positions are not "
            "strictly increasing."
        )

    return positions


def summarize_conflicts() -> dict:
    """
    Validate exact-conflict diagnostics without allowing future information
    to influence historical training data.
    """
    require_file(
        CONFLICT_FILE_PATH
    )

    conflicts = pd.read_csv(
        CONFLICT_FILE_PATH,
        usecols=[
            "partition",
            "Label",
            "exact_conflict_group_id",
        ],
        low_memory=False,
    )

    expected_partitions = {
        "training",
        "development",
        "post_benign",
    }

    actual_partitions = set(
        conflicts[
            "partition"
        ]
        .astype(str)
        .unique()
    )

    assert_equal(
        actual_partitions,
        expected_partitions,
        "Conflict-file partitions",
    )

    total_patterns = int(
        conflicts[
            "exact_conflict_group_id"
        ].nunique()
    )

    total_rows = int(
        len(conflicts)
    )

    training = conflicts.loc[
        conflicts["partition"]
        == "training"
    ]

    training_label_counts_by_group = (
        training
        .groupby(
            "exact_conflict_group_id"
        )["Label"]
        .nunique()
    )

    internal_group_ids = set(
        training_label_counts_by_group[
            training_label_counts_by_group
            > 1
        ].index
    )

    all_group_ids = set(
        conflicts[
            "exact_conflict_group_id"
        ].unique()
    )

    future_only_group_ids = (
        all_group_ids
        - internal_group_ids
    )

    internal_training_rows = (
        training.loc[
            training[
                "exact_conflict_group_id"
            ].isin(
                internal_group_ids
            )
        ]
    )

    internal_training_label_counts = {
        str(label): int(count)
        for label, count
        in sorted(
            internal_training_rows[
                "Label"
            ]
            .value_counts()
            .to_dict()
            .items()
        )
    }

    future_only_rows = (
        conflicts.loc[
            conflicts[
                "exact_conflict_group_id"
            ].isin(
                future_only_group_ids
            )
        ]
    )

    future_only_training = (
        future_only_rows.loc[
            future_only_rows[
                "partition"
            ]
            == "training"
        ]
    )

    future_only_future = (
        future_only_rows.loc[
            future_only_rows[
                "partition"
            ]
            != "training"
        ]
    )

    # Each future-only contradiction must represent a pattern already
    # seen in training that becomes contradictory only when a later
    # label is observed.
    future_groups_with_training = set(
        future_only_training[
            "exact_conflict_group_id"
        ].unique()
    )

    future_groups_with_future = set(
        future_only_future[
            "exact_conflict_group_id"
        ].unique()
    )

    assert_equal(
        future_groups_with_training,
        future_only_group_ids,
        "Future-only conflict groups represented in training",
    )

    assert_equal(
        future_groups_with_future,
        future_only_group_ids,
        "Future-only conflict groups represented in future partitions",
    )

    future_rows_per_group = (
        future_only_future
        .groupby(
            "exact_conflict_group_id"
        )
        .size()
    )

    if not (
        future_rows_per_group
        == 1
    ).all():
        raise AssertionError(
            "Expected exactly one future "
            "contradictory row per future-only pattern."
        )

    future_breakdown_series = (
        future_only_future
        .groupby(
            [
                "partition",
                "Label",
            ]
        )
        .size()
    )

    future_breakdown = {
        f"{partition}|{label}": int(count)
        for (
            partition,
            label,
        ), count
        in future_breakdown_series.items()
    }

    summary = {
        "total_conflict_patterns": (
            total_patterns
        ),
        "total_conflict_rows": (
            total_rows
        ),
        "training_internal_conflict_patterns": (
            len(
                internal_group_ids
            )
        ),
        "training_internal_conflict_rows": int(
            len(
                internal_training_rows
            )
        ),
        "training_internal_conflict_label_counts": (
            internal_training_label_counts
        ),
        "future_only_conflict_patterns": (
            len(
                future_only_group_ids
            )
        ),
        "future_only_training_rows": int(
            len(
                future_only_training
            )
        ),
        "future_only_future_rows": int(
            len(
                future_only_future
            )
        ),
        "future_only_future_partition_label_counts": (
            future_breakdown
        ),
    }

    assert_equal(
        summary,
        EXPECTED_CONFLICT_DIAGNOSTICS,
        "Exact conflict diagnostics",
    )

    return summary


def binary_summary(
    label_counts: dict[str, int],
) -> dict[str, int]:
    benign = int(
        label_counts.get(
            "BENIGN",
            0,
        )
    )

    total = int(
        sum(
            label_counts.values()
        )
    )

    return {
        "benign": benign,
        "attack": total - benign,
        "total": total,
    }


def main() -> None:
    print("=" * 72)
    print(
        "CICIDS2017 SUDDEN-BENIGN "
        "SCENARIO FREEZE"
    )
    print("=" * 72)

    MANIFEST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    require_file(
        REQUIREMENTS_LOCK_PATH
    )

    validate_environment()

    print(
        "Validating raw provenance..."
    )

    raw_manifest = (
        validate_raw_manifest()
    )

    print(
        "Validating preprocessing schema..."
    )

    preprocessing_manifest = (
        load_preprocessing_manifest()
    )

    print(
        "Validating label-conflict diagnostics..."
    )

    conflict_summary = (
        summarize_conflicts()
    )

    print(
        "Loading scenario metadata..."
    )

    # -----------------------------------------------------------------
    # Monday
    # -----------------------------------------------------------------
    monday = read_metadata(
        MONDAY,
        expected_source_order=0,
        expected_source_file=MONDAY_SOURCE,
        expected_rows=(
            EXPECTED_SOURCE_ROWS[
                MONDAY_SOURCE
            ]
        ),
    )

    monday_counts = (
        sorted_label_counts(
            monday
        )
    )

    del monday

    # -----------------------------------------------------------------
    # Tuesday
    # -----------------------------------------------------------------
    tuesday = read_metadata(
        TUESDAY,
        expected_source_order=1,
        expected_source_file=TUESDAY_SOURCE,
        expected_rows=(
            EXPECTED_SOURCE_ROWS[
                TUESDAY_SOURCE
            ]
        ),
    )

    tuesday_counts = (
        sorted_label_counts(
            tuesday
        )
    )

    del tuesday

    # -----------------------------------------------------------------
    # Wednesday
    # -----------------------------------------------------------------
    wednesday = read_metadata(
        WEDNESDAY,
        expected_source_order=2,
        expected_source_file=WEDNESDAY_SOURCE,
        expected_rows=(
            EXPECTED_SOURCE_ROWS[
                WEDNESDAY_SOURCE
            ]
        ),
    )

    train_wednesday = (
        wednesday.iloc[
            TRAIN_WEDNESDAY_START:
            TRAIN_WEDNESDAY_END
        ]
    )

    development = (
        wednesday.iloc[
            DEVELOPMENT_START:
            DEVELOPMENT_END
        ]
    )

    pre_drift_raw = (
        wednesday.iloc[
            PRE_DRIFT_START:
            PRE_DRIFT_END
        ]
    )

    post_template = (
        wednesday.iloc[
            POST_DRIFT_TEMPLATE_START:
            POST_DRIFT_TEMPLATE_END
        ]
    )

    heartbleed_rows = int(
        (
            pre_drift_raw[
                "Label"
            ]
            == "Heartbleed"
        ).sum()
    )

    assert_equal(
        heartbleed_rows,
        11,
        "Excluded Heartbleed count",
    )

    pre_drift = (
        pre_drift_raw.loc[
            pre_drift_raw[
                "Label"
            ]
            != "Heartbleed"
        ]
    )

    post_template_labels = set(
        post_template[
            "Label"
        ].astype(str)
    )

    assert_equal(
        post_template_labels,
        {
            "BENIGN",
            "DoS GoldenEye",
        },
        "Post-drift template label set",
    )

    post_attack = (
        post_template.loc[
            post_template[
                "Label"
            ]
            == "DoS GoldenEye"
        ]
    )

    post_benign_slots = (
        post_template.loc[
            post_template[
                "Label"
            ]
            == "BENIGN",
            "row_in_source",
        ]
        .to_numpy(
            dtype=np.int64,
            copy=True,
        )
    )

    assert_equal(
        len(
            post_benign_slots
        ),
        POST_BENIGN_REQUIRED,
        "Post-template BENIGN slots",
    )

    # -----------------------------------------------------------------
    # Thursday-morning BENIGN replacement source
    # -----------------------------------------------------------------
    thursday = read_metadata(
        THURSDAY_MORNING,
        expected_source_order=3,
        expected_source_file=(
            THURSDAY_MORNING_SOURCE
        ),
        expected_rows=(
            EXPECTED_SOURCE_ROWS[
                THURSDAY_MORNING_SOURCE
            ]
        ),
    )

    thursday_benign = (
        thursday.loc[
            thursday[
                "Label"
            ]
            == "BENIGN"
        ]
        .reset_index(
            drop=True
        )
    )

    assert_equal(
        len(
            thursday_benign
        ),
        168_186,
        "Thursday-morning BENIGN count",
    )

    selection_positions = (
        deterministic_positions(
            total_rows=len(
                thursday_benign
            ),
            requested_rows=(
                POST_BENIGN_REQUIRED
            ),
        )
    )

    selected_thursday_benign = (
        thursday_benign.iloc[
            selection_positions
        ]
    )

    selected_thursday_row_ids = (
        selected_thursday_benign[
            "row_in_source"
        ]
        .to_numpy(
            dtype=np.int64,
            copy=True,
        )
    )

    if (
        len(
            np.unique(
                selected_thursday_row_ids
            )
        )
        != POST_BENIGN_REQUIRED
    ):
        raise AssertionError(
            "Selected Thursday source row IDs "
            "are not unique."
        )

    selected_source_hash = (
        sha256_int64_array(
            selected_thursday_row_ids
        )
    )

    template_slot_hash = (
        sha256_int64_array(
            post_benign_slots
        )
    )

    mapping_hash = (
        sha256_int64_pairs(
            post_benign_slots,
            selected_thursday_row_ids,
        )
    )

    assert_equal(
        selected_source_hash,
        EXPECTED_POST_BENIGN_SOURCE_ROW_ID_SHA256,
        "Selected Thursday BENIGN source-row SHA-256",
    )

    assert_equal(
        template_slot_hash,
        EXPECTED_POST_BENIGN_TEMPLATE_SLOT_SHA256,
        "Post-template BENIGN slot SHA-256",
    )

    assert_equal(
        mapping_hash,
        EXPECTED_POST_BENIGN_MAPPING_SHA256,
        "Post-drift BENIGN slot-to-source mapping SHA-256",
    )

    del thursday

    # -----------------------------------------------------------------
    # Final label-count validation
    # -----------------------------------------------------------------
    train_counts = (
        merge_label_counts(
            monday_counts,
            tuesday_counts,
            sorted_label_counts(
                train_wednesday
            ),
        )
    )

    development_counts = (
        sorted_label_counts(
            development
        )
    )

    pre_drift_counts = (
        sorted_label_counts(
            pre_drift
        )
    )

    post_attack_counts = (
        sorted_label_counts(
            post_attack
        )
    )

    assert_equal(
        train_counts,
        EXPECTED_TRAIN_LABELS,
        "Training label counts",
    )

    assert_equal(
        development_counts,
        EXPECTED_DEVELOPMENT_LABELS,
        "Development label counts",
    )

    assert_equal(
        pre_drift_counts,
        EXPECTED_PRE_DRIFT_LABELS,
        "Pre-drift label counts",
    )

    assert_equal(
        post_attack_counts,
        {
            "DoS GoldenEye": 3_573,
        },
        "Post-drift attack count",
    )

    post_drift_counts = {
        "BENIGN": (
            POST_BENIGN_REQUIRED
        ),
        "DoS GoldenEye": (
            3_573
        ),
    }

    assert_equal(
        post_drift_counts,
        EXPECTED_POST_DRIFT_LABELS,
        "Post-drift label counts",
    )

    # -----------------------------------------------------------------
    # Freeze scenario specification
    # -----------------------------------------------------------------
    generator_path = Path(
        __file__
    ).resolve()

    manifest = {
        "manifest_format_version": 1,
        "scenario_id": (
            "cicids2017_sudden_benign_v1"
        ),
        "scenario_version": 1,
        "dataset": "CICIDS2017",
        "task": (
            "binary_intrusion_detection"
        ),
        "binary_target_mapping": {
            "BENIGN": 0,
            "all_other_labels": 1,
        },
        "chronology": {
            "type": (
                "pseudo-chronological"
            ),
            "timestamps_available": False,
            "claim": (
                "Source-file order and original "
                "row order are preserved. "
                "True timestamp chronology is not "
                "claimed because timestamps are "
                "absent from the MachineLearningCSV "
                "feature tables used here."
            ),
        },
        "construction": {
            "type": (
                "controlled_synthetic_composite"
            ),
            "drift_type": (
                "benign_source_regime_covariate_shift"
            ),
            "purpose": (
                "Introduce an abrupt BENIGN "
                "source-regime covariate shift while "
                "retaining the DoS GoldenEye attack "
                "family and closely matching pre/post "
                "attack prevalence."
            ),
            "natural_production_drift_claim": False,
        },
        "environment": {
            "python_version": (
                platform.python_version()
            ),
            "requirements_lock_file": (
                REQUIREMENTS_LOCK_PATH
                .relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            ),
            "requirements_lock_sha256": (
                sha256_file(
                    REQUIREMENTS_LOCK_PATH
                )
            ),
            "requirements_lock_normalized_text_sha256": (
                sha256_normalized_text(
                    REQUIREMENTS_LOCK_PATH
                )
            ),
        },
        "generator": {
            "file": (
                generator_path
                .relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            ),
            "sha256": (
                sha256_file(
                    generator_path
                )
            ),
            "normalized_text_sha256": (
                sha256_normalized_text(
                    generator_path
                )
            ),
        },
        "provenance": {
            "raw_manifest_file": (
                RAW_MANIFEST_PATH
                .relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            ),
            "raw_manifest_sha256": (
                sha256_file(
                    RAW_MANIFEST_PATH
                )
            ),
            "raw_manifest_canonical_sha256": (
                sha256_canonical_json(
                    RAW_MANIFEST_PATH
                )
            ),
            "preprocessing_manifest_file": (
                PREPROCESSING_MANIFEST_PATH
                .relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            ),
            "preprocessing_manifest_sha256": (
                sha256_file(
                    PREPROCESSING_MANIFEST_PATH
                )
            ),
            "preprocessing_manifest_canonical_sha256": (
                sha256_canonical_json(
                    PREPROCESSING_MANIFEST_PATH
                )
            ),
            "exact_conflict_file": (
                CONFLICT_FILE_PATH
                .relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            ),
            "exact_conflict_file_sha256": (
                sha256_file(
                    CONFLICT_FILE_PATH
                )
            ),
            "exact_conflict_projection_sha256": (
                sha256_conflict_projection(
                    CONFLICT_FILE_PATH
                )
            ),
            "raw_dataset_total_rows": (
                raw_manifest[
                    "total_rows"
                ]
            ),
        },
        "feature_schema": {
            "model_feature_count": (
                EXPECTED_FEATURE_COUNT
            ),
            "feature_columns": (
                preprocessing_manifest[
                    "feature_columns"
                ]
            ),
            "model_excludes": [
                "source_file",
                "source_order",
                "row_in_source",
                "Label",
            ],
        },
        "partitions": {
            "training": {
                "rows": int(
                    sum(
                        train_counts.values()
                    )
                ),
                "label_counts": (
                    train_counts
                ),
                "binary_counts": (
                    binary_summary(
                        train_counts
                    )
                ),
                "components": [
                    {
                        "source_file": (
                            MONDAY_SOURCE
                        ),
                        "source_order": 0,
                        "row_start_inclusive": 0,
                        "row_end_exclusive": (
                            EXPECTED_SOURCE_ROWS[
                                MONDAY_SOURCE
                            ]
                        ),
                    },
                    {
                        "source_file": (
                            TUESDAY_SOURCE
                        ),
                        "source_order": 1,
                        "row_start_inclusive": 0,
                        "row_end_exclusive": (
                            EXPECTED_SOURCE_ROWS[
                                TUESDAY_SOURCE
                            ]
                        ),
                    },
                    {
                        "source_file": (
                            WEDNESDAY_SOURCE
                        ),
                        "source_order": 2,
                        "row_start_inclusive": (
                            TRAIN_WEDNESDAY_START
                        ),
                        "row_end_exclusive": (
                            TRAIN_WEDNESDAY_END
                        ),
                    },
                ],
            },
            "development": {
                "rows": int(
                    len(
                        development
                    )
                ),
                "label_counts": (
                    development_counts
                ),
                "binary_counts": (
                    binary_summary(
                        development_counts
                    )
                ),
                "source_file": (
                    WEDNESDAY_SOURCE
                ),
                "source_order": 2,
                "row_start_inclusive": (
                    DEVELOPMENT_START
                ),
                "row_end_exclusive": (
                    DEVELOPMENT_END
                ),
            },
            "pre_drift": {
                "rows": int(
                    len(
                        pre_drift
                    )
                ),
                "label_counts": (
                    pre_drift_counts
                ),
                "binary_counts": (
                    binary_summary(
                        pre_drift_counts
                    )
                ),
                "source_file": (
                    WEDNESDAY_SOURCE
                ),
                "source_order": 2,
                "row_start_inclusive": (
                    PRE_DRIFT_START
                ),
                "row_end_exclusive": (
                    PRE_DRIFT_END
                ),
                "excluded_labels": {
                    "Heartbleed": 11,
                },
            },
            "post_drift": {
                "rows": int(
                    sum(
                        post_drift_counts.values()
                    )
                ),
                "label_counts": (
                    post_drift_counts
                ),
                "binary_counts": (
                    binary_summary(
                        post_drift_counts
                    )
                ),
                "template": {
                    "source_file": (
                        WEDNESDAY_SOURCE
                    ),
                    "source_order": 2,
                    "row_start_inclusive": (
                        POST_DRIFT_TEMPLATE_START
                    ),
                    "row_end_exclusive": (
                        POST_DRIFT_TEMPLATE_END
                    ),
                    "attack_rows_retained": (
                        3_573
                    ),
                    "retained_attack_label": (
                        "DoS GoldenEye"
                    ),
                    "benign_slots_replaced": (
                        POST_BENIGN_REQUIRED
                    ),
                },
                "benign_replacement": {
                    "source_file": (
                        THURSDAY_MORNING_SOURCE
                    ),
                    "source_order": 3,
                    "eligible_label": (
                        "BENIGN"
                    ),
                    "eligible_rows": (
                        168_186
                    ),
                    "selected_rows": (
                        POST_BENIGN_REQUIRED
                    ),
                    "selection_method": (
                        "Filter Thursday-morning "
                        "BENIGN rows while preserving "
                        "source order, then select "
                        "eligible position[k] = "
                        "floor(k * 168186 / 65697) "
                        "for k=0..65696."
                    ),
                    "assembly_method": (
                        "Preserve Wednesday post-template "
                        "row order. Retain each "
                        "DoS GoldenEye row in its original "
                        "template position. For BENIGN "
                        "template slots in ascending "
                        "row_in_source order, replace "
                        "slot j with selected Thursday "
                        "BENIGN row j."
                    ),
                    "selected_source_row_id_sha256": (
                        selected_source_hash
                    ),
                    "template_benign_slot_row_id_sha256": (
                        template_slot_hash
                    ),
                    "slot_to_source_row_id_mapping_sha256": (
                        mapping_hash
                    ),
                    "first_selected_source_row": int(
                        selected_thursday_row_ids[
                            0
                        ]
                    ),
                    "last_selected_source_row": int(
                        selected_thursday_row_ids[
                            -1
                        ]
                    ),
                    "first_template_benign_slot": int(
                        post_benign_slots[
                            0
                        ]
                    ),
                    "last_template_benign_slot": int(
                        post_benign_slots[
                            -1
                        ]
                    ),
                },
            },
        },
        "data_quality_policy": {
            "duplicate_rows": {
                "primary_policy": (
                    "retain"
                ),
                "rationale": (
                    "Repeated observations are "
                    "preserved in the operational "
                    "pseudo-chronological stream."
                ),
                "drift_detector_stream_policy": (
                    "full_stream_including_repeats"
                ),
                "evaluation_policy": (
                    "Primary metrics use the full "
                    "stream. Additional metrics will "
                    "separately report observations "
                    "whose exact feature pattern was "
                    "not present in training."
                ),
                "planned_sensitivity_analysis": (
                    "deduplicated_training"
                ),
            },
            "representation_level_label_conflicts": {
                "primary_policy": (
                    "retain_original_rows_and_labels"
                ),
                "rationale": (
                    "Identical 77-feature vectors with "
                    "different labels are treated as "
                    "representation-level label "
                    "contradictions, not proven "
                    "annotation errors. No majority "
                    "relabeling or future-informed "
                    "deletion is used."
                ),
                "diagnostics": (
                    conflict_summary
                ),
                "planned_sensitivity_analysis": (
                    "training_internal_conflict_removal"
                ),
            },
            "future_information_policy": (
                "Future development or post-drift "
                "labels must never alter historical "
                "training rows, labels, preprocessing, "
                "feature transformations, or scenario "
                "construction decisions."
            ),
        },
    }

    with OUTPUT_MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        )

        file.write("\n")

    print("\n" + "=" * 72)
    print(
        "SCENARIO FROZEN SUCCESSFULLY"
    )
    print("=" * 72)

    print(
        "Training rows:      "
        f"{manifest['partitions']['training']['rows']:,}"
    )

    print(
        "Development rows:   "
        f"{manifest['partitions']['development']['rows']:,}"
    )

    print(
        "Pre-drift rows:     "
        f"{manifest['partitions']['pre_drift']['rows']:,}"
    )

    print(
        "Post-drift rows:    "
        f"{manifest['partitions']['post_drift']['rows']:,}"
    )

    print(
        "Training conflicts: "
        f"{conflict_summary['training_internal_conflict_patterns']} "
        "patterns / "
        f"{conflict_summary['training_internal_conflict_rows']:,} "
        "rows (retained)"
    )

    print(
        "Future-only conflicting patterns: "
        f"{conflict_summary['future_only_conflict_patterns']} "
        "(not used to alter training)"
    )

    print(
        "Post BENIGN selection SHA-256: "
        f"{selected_source_hash}"
    )

    print(
        "Post BENIGN mapping SHA-256:   "
        f"{mapping_hash}"
    )

    print(
        "\nManifest written to:"
    )

    print(
        OUTPUT_MANIFEST_PATH
    )


if __name__ == "__main__":
    main()