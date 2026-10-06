from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


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
    / "regime_diagnostics"
)

PREPROCESSING_MANIFEST = (
    INTERIM_DIR
    / "preprocessing_manifest.json"
)


WEDNESDAY_FILE = (
    "Wednesday-workingHours.pcap_ISCX.csv.gz"
)

THURSDAY_MORNING_FILE = (
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.gz"
)


# Wednesday window 9
PRE_DRIFT_START = 554_162
PRE_DRIFT_END = 623_433

# Wednesday window 10
POST_ATTACK_START = 623_433
POST_ATTACK_END = 692_703

MAX_BENIGN_SAMPLE = 50_000


def load_feature_columns() -> list[str]:
    with PREPROCESSING_MANIFEST.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    feature_columns = manifest.get(
        "feature_columns"
    )

    if not feature_columns:
        raise ValueError(
            "No feature_columns found in preprocessing manifest."
        )

    if len(feature_columns) != 77:
        raise ValueError(
            f"Expected 77 model features, found "
            f"{len(feature_columns)}."
        )

    return feature_columns


def deterministic_sample(
    df: pd.DataFrame,
    maximum_rows: int,
) -> pd.DataFrame:
    """
    Select rows deterministically while preserving their order.

    No random sampling is used.
    """
    if len(df) <= maximum_rows:
        return df.reset_index(drop=True)

    positions = (
        np.arange(
            maximum_rows,
            dtype=np.int64,
        )
        * len(df)
        // maximum_rows
    )

    return (
        df.iloc[positions]
        .reset_index(drop=True)
    )


def finite_values(
    series: pd.Series,
) -> np.ndarray:
    values = series.to_numpy(
        dtype=np.float64,
        copy=True,
    )

    return values[
        np.isfinite(values)
    ]


def compare_feature_distributions(
    before: pd.DataFrame,
    after: pd.DataFrame,
    feature_columns: list[str],
    comparison_name: str,
) -> pd.DataFrame:
    records = []

    for feature in feature_columns:
        before_values = finite_values(
            before[feature]
        )

        after_values = finite_values(
            after[feature]
        )

        if (
            len(before_values) == 0
            or len(after_values) == 0
        ):
            records.append(
                {
                    "comparison": comparison_name,
                    "feature": feature,
                    "before_n": len(before_values),
                    "after_n": len(after_values),
                    "ks_statistic": np.nan,
                    "ks_pvalue": np.nan,
                    "before_median": np.nan,
                    "after_median": np.nan,
                    "before_iqr": np.nan,
                    "robust_median_shift": np.nan,
                }
            )
            continue

        result = ks_2samp(
            before_values,
            after_values,
            alternative="two-sided",
            method="asymp",
        )

        before_q25, before_median, before_q75 = (
            np.percentile(
                before_values,
                [25, 50, 75],
            )
        )

        after_median = float(
            np.median(after_values)
        )

        before_iqr = float(
            before_q75 - before_q25
        )

        if before_iqr > 0:
            robust_shift = (
                after_median
                - before_median
            ) / before_iqr
        else:
            robust_shift = np.nan

        records.append(
            {
                "comparison": comparison_name,
                "feature": feature,
                "before_n": len(before_values),
                "after_n": len(after_values),
                "ks_statistic": float(
                    result.statistic
                ),
                "ks_pvalue": float(
                    result.pvalue
                ),
                "before_median": float(
                    before_median
                ),
                "after_median": float(
                    after_median
                ),
                "before_iqr": before_iqr,
                "robust_median_shift": (
                    float(robust_shift)
                    if np.isfinite(
                        robust_shift
                    )
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(records)


def summarize_comparison(
    results: pd.DataFrame,
) -> dict:
    ks = (
        results["ks_statistic"]
        .dropna()
        .to_numpy(
            dtype=np.float64
        )
    )

    return {
        "features_evaluated": int(
            len(ks)
        ),
        "mean_ks": float(
            np.mean(ks)
        ),
        "median_ks": float(
            np.median(ks)
        ),
        "p90_ks": float(
            np.percentile(
                ks,
                90,
            )
        ),
        "max_ks": float(
            np.max(ks)
        ),
        "features_ks_ge_0_10": int(
            (ks >= 0.10).sum()
        ),
        "features_ks_ge_0_20": int(
            (ks >= 0.20).sum()
        ),
        "features_ks_ge_0_30": int(
            (ks >= 0.30).sum()
        ),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_columns = (
        load_feature_columns()
    )

    columns_to_read = (
        [
            "row_in_source",
            "Label",
        ]
        + feature_columns
    )

    print("=" * 72)
    print("CICIDS2017 REGIME DIAGNOSTICS")
    print("=" * 72)

    # -----------------------------------------------------
    # Load Wednesday
    # -----------------------------------------------------
    wednesday_path = (
        INTERIM_DIR
        / WEDNESDAY_FILE
    )

    print(
        f"Loading: {wednesday_path.name}"
    )

    wednesday = pd.read_csv(
        wednesday_path,
        usecols=columns_to_read,
        low_memory=False,
    )

    # Pre-drift benign: Wednesday window 9
    pre_benign = wednesday.loc[
        (
            wednesday["row_in_source"]
            >= PRE_DRIFT_START
        )
        & (
            wednesday["row_in_source"]
            < PRE_DRIFT_END
        )
        & (
            wednesday["Label"]
            == "BENIGN"
        )
    ]

    # Pre-drift GoldenEye: Wednesday window 9
    pre_attack = wednesday.loc[
        (
            wednesday["row_in_source"]
            >= PRE_DRIFT_START
        )
        & (
            wednesday["row_in_source"]
            < PRE_DRIFT_END
        )
        & (
            wednesday["Label"]
            == "DoS GoldenEye"
        )
    ]

    # Post-boundary GoldenEye: Wednesday window 10
    post_attack = wednesday.loc[
        (
            wednesday["row_in_source"]
            >= POST_ATTACK_START
        )
        & (
            wednesday["row_in_source"]
            < POST_ATTACK_END
        )
        & (
            wednesday["Label"]
            == "DoS GoldenEye"
        )
    ]

    # -----------------------------------------------------
    # Load Thursday morning
    # -----------------------------------------------------
    thursday_path = (
        INTERIM_DIR
        / THURSDAY_MORNING_FILE
    )

    print(
        f"Loading: {thursday_path.name}"
    )

    thursday = pd.read_csv(
        thursday_path,
        usecols=columns_to_read,
        low_memory=False,
    )

    post_benign = thursday.loc[
        thursday["Label"] == "BENIGN"
    ]

    # Equal-size, deterministic benign comparison.
    pre_benign_sample = (
        deterministic_sample(
            pre_benign,
            MAX_BENIGN_SAMPLE,
        )
    )

    post_benign_sample = (
        deterministic_sample(
            post_benign,
            MAX_BENIGN_SAMPLE,
        )
    )

    print()
    print(
        "Pre-drift BENIGN rows:   "
        f"{len(pre_benign):,}"
    )
    print(
        "Thursday BENIGN rows:    "
        f"{len(post_benign):,}"
    )
    print(
        "Pre GoldenEye rows:      "
        f"{len(pre_attack):,}"
    )
    print(
        "Post GoldenEye rows:     "
        f"{len(post_attack):,}"
    )

    if len(pre_attack) != 3_589:
        raise ValueError(
            "Unexpected pre-drift GoldenEye count: "
            f"{len(pre_attack)}"
        )

    if len(post_attack) != 3_573:
        raise ValueError(
            "Unexpected post-drift GoldenEye count: "
            f"{len(post_attack)}"
        )

    # -----------------------------------------------------
    # Compare benign regime shift
    # -----------------------------------------------------
    benign_results = (
        compare_feature_distributions(
            before=pre_benign_sample,
            after=post_benign_sample,
            feature_columns=feature_columns,
            comparison_name=(
                "Wednesday_W9_BENIGN_vs_"
                "Thursday_AM_BENIGN"
            ),
        )
    )

    # -----------------------------------------------------
    # Compare attack stability
    # -----------------------------------------------------
    attack_results = (
        compare_feature_distributions(
            before=pre_attack,
            after=post_attack,
            feature_columns=feature_columns,
            comparison_name=(
                "Wednesday_W9_GoldenEye_vs_"
                "Wednesday_W10_GoldenEye"
            ),
        )
    )

    benign_results.to_csv(
        OUTPUT_DIR
        / "benign_regime_shift.csv",
        index=False,
    )

    attack_results.to_csv(
        OUTPUT_DIR
        / "goldeneye_stability.csv",
        index=False,
    )

    benign_summary = (
        summarize_comparison(
            benign_results
        )
    )

    attack_summary = (
        summarize_comparison(
            attack_results
        )
    )

    summary = {
        "pre_drift_benign_rows": int(
            len(pre_benign)
        ),
        "post_drift_benign_rows_available": int(
            len(post_benign)
        ),
        "benign_comparison_sample_size_each": int(
            min(
                MAX_BENIGN_SAMPLE,
                len(pre_benign),
                len(post_benign),
            )
        ),
        "pre_drift_goldeneye_rows": int(
            len(pre_attack)
        ),
        "post_drift_goldeneye_rows": int(
            len(post_attack)
        ),
        "benign_regime_shift": (
            benign_summary
        ),
        "goldeneye_temporal_stability": (
            attack_summary
        ),
    }

    with (
        OUTPUT_DIR
        / "regime_diagnostics_summary.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # -----------------------------------------------------
    # Console summaries
    # -----------------------------------------------------
    print("\n" + "=" * 72)
    print("BENIGN REGIME SHIFT")
    print("=" * 72)

    for key, value in (
        benign_summary.items()
    ):
        print(
            f"{key:24s}: {value}"
        )

    print("\nTop 10 shifted BENIGN features:")

    print(
        benign_results
        .sort_values(
            "ks_statistic",
            ascending=False,
        )
        .head(10)[
            [
                "feature",
                "ks_statistic",
                "before_median",
                "after_median",
                "robust_median_shift",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print("\n" + "=" * 72)
    print("GOLDENEYE TEMPORAL STABILITY")
    print("=" * 72)

    for key, value in (
        attack_summary.items()
    ):
        print(
            f"{key:24s}: {value}"
        )

    print("\nTop 10 shifted GoldenEye features:")

    print(
        attack_results
        .sort_values(
            "ks_statistic",
            ascending=False,
        )
        .head(10)[
            [
                "feature",
                "ks_statistic",
                "before_median",
                "after_median",
                "robust_median_shift",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print("\nOutputs written to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()