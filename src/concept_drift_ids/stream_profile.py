from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERIM_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "cicids2017"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "results"
    / "stream_profile"
)


EXPECTED_FILES = [
    "Monday-WorkingHours.pcap_ISCX.csv.gz",
    "Tuesday-WorkingHours.pcap_ISCX.csv.gz",
    "Wednesday-workingHours.pcap_ISCX.csv.gz",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.gz",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv.gz",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv.gz",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.gz",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.gz",
]


WINDOW_COUNT = 10


def profile_file(
    path: Path,
    expected_source_order: int,
) -> tuple[list[dict], list[dict], dict]:
    """
    Profile label positions and contiguous windows without modifying data.
    """
    print(f"Profiling: {path.name}")

    df = pd.read_csv(
        path,
        usecols=[
            "source_file",
            "source_order",
            "row_in_source",
            "Label",
        ],
        low_memory=False,
    )

    if df.empty:
        raise ValueError(f"File is empty: {path.name}")

    source_files = df["source_file"].unique()

    if len(source_files) != 1:
        raise ValueError(
            f"Expected one source_file in {path.name}, "
            f"found {len(source_files)}"
        )

    source_orders = df["source_order"].unique()

    if (
        len(source_orders) != 1
        or int(source_orders[0]) != expected_source_order
    ):
        raise ValueError(
            f"Unexpected source_order in {path.name}: "
            f"{source_orders}"
        )

    expected_rows = pd.RangeIndex(
        start=0,
        stop=len(df),
        step=1,
    )

    actual_rows = pd.Index(
        df["row_in_source"]
    )

    if not actual_rows.equals(expected_rows):
        raise ValueError(
            f"row_in_source is not contiguous in {path.name}"
        )

    source_file = str(source_files[0])
    total_rows = len(df)

    # ---------------------------------------------------------
    # Label position summary
    # ---------------------------------------------------------
    label_position_records = []

    grouped = df.groupby(
        "Label",
        sort=False,
        observed=True,
    )

    for label, group in grouped:
        positions = group["row_in_source"]

        first_row = int(positions.min())
        last_row = int(positions.max())
        count = len(group)

        first_fraction = first_row / total_rows
        last_fraction = last_row / total_rows

        label_position_records.append(
            {
                "source_file": source_file,
                "source_order": expected_source_order,
                "label": str(label),
                "count": int(count),
                "first_row": first_row,
                "last_row": last_row,
                "first_fraction": first_fraction,
                "last_fraction": last_fraction,
            }
        )

    # ---------------------------------------------------------
    # Fixed contiguous windows
    # ---------------------------------------------------------
    window_records = []

    for window_index in range(WINDOW_COUNT):
        start = round(
            window_index
            * total_rows
            / WINDOW_COUNT
        )

        end = round(
            (window_index + 1)
            * total_rows
            / WINDOW_COUNT
        )

        window = df.iloc[start:end]

        counts = (
            window["Label"]
            .value_counts(dropna=False)
        )

        for label, count in counts.items():
            window_records.append(
                {
                    "source_file": source_file,
                    "source_order": expected_source_order,
                    "window": window_index + 1,
                    "window_start_row": start,
                    "window_end_row_exclusive": end,
                    "window_rows": end - start,
                    "label": str(label),
                    "count": int(count),
                    "fraction_of_window": (
                        int(count) / (end - start)
                    ),
                }
            )

    file_summary = {
        "source_file": source_file,
        "source_order": expected_source_order,
        "rows": total_rows,
        "labels": {
            str(label): int(count)
            for label, count in (
                df["Label"]
                .value_counts(dropna=False)
                .items()
            )
        },
    }

    return (
        label_position_records,
        window_records,
        file_summary,
    )


def main() -> None:
    if not INTERIM_DATA_DIR.exists():
        raise FileNotFoundError(
            "Interim CICIDS2017 directory not found:\n"
            f"{INTERIM_DATA_DIR}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_label_positions = []
    all_windows = []
    file_summaries = []

    print("=" * 72)
    print("CICIDS2017 PSEUDO-CHRONOLOGICAL STREAM PROFILE")
    print("=" * 72)

    for source_order, filename in enumerate(
        EXPECTED_FILES
    ):
        path = INTERIM_DATA_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Expected interim file not found:\n{path}"
            )

        (
            label_positions,
            windows,
            summary,
        ) = profile_file(
            path=path,
            expected_source_order=source_order,
        )

        all_label_positions.extend(
            label_positions
        )

        all_windows.extend(
            windows
        )

        file_summaries.append(
            summary
        )

    positions_df = pd.DataFrame(
        all_label_positions
    )

    windows_df = pd.DataFrame(
        all_windows
    )

    positions_df.to_csv(
        OUTPUT_DIR / "label_positions.csv",
        index=False,
    )

    windows_df.to_csv(
        OUTPUT_DIR / "window_label_counts.csv",
        index=False,
    )

    manifest = {
        "dataset": "CICIDS2017",
        "purpose": (
            "Pseudo-chronological stream profiling "
            "before experimental split construction"
        ),
        "window_count_per_source_file": WINDOW_COUNT,
        "file_count": len(file_summaries),
        "files": file_summaries,
    }

    with (
        OUTPUT_DIR / "stream_profile_manifest.json"
    ).open(
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
    print("LABEL POSITION SUMMARY")
    print("=" * 72)

    display_columns = [
        "source_file",
        "label",
        "count",
        "first_row",
        "last_row",
        "first_fraction",
        "last_fraction",
    ]

    print(
        positions_df[
            display_columns
        ].to_string(
            index=False,
            formatters={
                "first_fraction": (
                    lambda value:
                    f"{value:.4f}"
                ),
                "last_fraction": (
                    lambda value:
                    f"{value:.4f}"
                ),
            },
        )
    )

    print("\nOutputs written to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()