from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import t


PRIMARY_CONFIRMATORY_ENDPOINTS = (
    "E1_post_mcc_d_drift_minus_c",
    "E2_post_mcsc_d_drift_minus_c",
    "E3_post_mcsc_d_drift_minus_d_periodic",
)


@dataclass(frozen=True)
class PairedEffectSummary:
    endpoint: str
    effects: tuple[float, ...]
    mean: float
    median: float
    sample_sd: float
    ci95_low: float
    ci95_high: float
    minimum: float
    maximum: float
    positive: int
    zero: int
    negative: int
    leave_one_seed_out_mean_min: float
    leave_one_seed_out_mean_max: float
    sign_test_n_effective: int
    sign_test_positive: int
    sign_test_p_one_sided: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "effects": list(self.effects),
            "mean": self.mean,
            "median": self.median,
            "sample_sd": self.sample_sd,
            "ci95_low": self.ci95_low,
            "ci95_high": self.ci95_high,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "positive": self.positive,
            "zero": self.zero,
            "negative": self.negative,
            "leave_one_seed_out_mean_min": self.leave_one_seed_out_mean_min,
            "leave_one_seed_out_mean_max": self.leave_one_seed_out_mean_max,
            "sign_test_n_effective": self.sign_test_n_effective,
            "sign_test_positive": self.sign_test_positive,
            "sign_test_p_one_sided": self.sign_test_p_one_sided,
        }


def exact_one_sided_sign_pvalue(
    *,
    positive: int,
    n_effective: int,
) -> float:
    if n_effective < 0:
        raise ValueError("n_effective must be non-negative.")
    if positive < 0 or positive > n_effective:
        raise ValueError("positive count must lie within [0,n_effective].")
    if n_effective == 0:
        return 1.0
    numerator = sum(
        math.comb(n_effective, k)
        for k in range(positive, n_effective + 1)
    )
    return float(numerator / (2 ** n_effective))


def paired_effect_summary(
    endpoint: str,
    effects: Sequence[float],
) -> PairedEffectSummary:
    values = np.asarray(effects, dtype=np.float64)
    if values.shape != (5,):
        raise ValueError(
            "Primary paired-effect summary requires exactly five seed effects."
        )
    if not np.isfinite(values).all():
        raise ValueError("Paired effects must be finite.")

    mean = float(values.mean())
    median = float(np.median(values))
    sample_sd = float(values.std(ddof=1))
    sem = sample_sd / math.sqrt(5.0)
    margin = float(t.ppf(0.975, df=4) * sem)
    positive = int(np.sum(values > 0))
    zero = int(np.sum(values == 0))
    negative = int(np.sum(values < 0))
    n_effective = positive + negative
    leave_one_out = tuple(
        float(np.delete(values, index).mean())
        for index in range(5)
    )

    return PairedEffectSummary(
        endpoint=str(endpoint),
        effects=tuple(float(value) for value in values),
        mean=mean,
        median=median,
        sample_sd=sample_sd,
        ci95_low=mean - margin,
        ci95_high=mean + margin,
        minimum=float(values.min()),
        maximum=float(values.max()),
        positive=positive,
        zero=zero,
        negative=negative,
        leave_one_seed_out_mean_min=min(leave_one_out),
        leave_one_seed_out_mean_max=max(leave_one_out),
        sign_test_n_effective=n_effective,
        sign_test_positive=positive,
        sign_test_p_one_sided=exact_one_sided_sign_pvalue(
            positive=positive,
            n_effective=n_effective,
        ),
    )


def holm_bonferroni(
    pvalues: Mapping[str, float],
) -> dict[str, float]:
    if not pvalues:
        return {}
    for name, value in pvalues.items():
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"Invalid p-value for {name}: {value}")

    ordered = sorted(
        ((name, float(value)) for name, value in pvalues.items()),
        key=lambda item: (item[1], item[0]),
    )
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, value) in enumerate(ordered):
        raw_adjusted = min(1.0, (m - rank) * value)
        running = max(running, raw_adjusted)
        adjusted[name] = running
    return adjusted


def build_confirmatory_family(
    *,
    d_drift_mcc_by_seed: Mapping[int, float],
    c_mcc_by_seed: Mapping[int, float],
    d_drift_mcsc_by_seed: Mapping[int, float],
    c_mcsc_by_seed: Mapping[int, float],
    d_periodic_mcsc_by_seed: Mapping[int, float],
) -> dict[str, Any]:
    seeds = (0, 1, 2, 3, 4)
    mappings = (
        d_drift_mcc_by_seed,
        c_mcc_by_seed,
        d_drift_mcsc_by_seed,
        c_mcsc_by_seed,
        d_periodic_mcsc_by_seed,
    )
    if any(tuple(sorted(mapping)) != seeds for mapping in mappings):
        raise ValueError(
            "Confirmatory family requires exactly seed keys 0,1,2,3,4."
        )

    effects = {
        PRIMARY_CONFIRMATORY_ENDPOINTS[0]: [
            float(d_drift_mcc_by_seed[seed])
            - float(c_mcc_by_seed[seed])
            for seed in seeds
        ],
        PRIMARY_CONFIRMATORY_ENDPOINTS[1]: [
            float(d_drift_mcsc_by_seed[seed])
            - float(c_mcsc_by_seed[seed])
            for seed in seeds
        ],
        PRIMARY_CONFIRMATORY_ENDPOINTS[2]: [
            float(d_drift_mcsc_by_seed[seed])
            - float(d_periodic_mcsc_by_seed[seed])
            for seed in seeds
        ],
    }
    summaries = {
        name: paired_effect_summary(name, values)
        for name, values in effects.items()
    }
    raw_p = {
        name: summary.sign_test_p_one_sided
        for name, summary in summaries.items()
    }
    adjusted = holm_bonferroni(raw_p)
    return {
        "endpoint_order": list(PRIMARY_CONFIRMATORY_ENDPOINTS),
        "summaries": {
            name: summary.to_dict()
            for name, summary in summaries.items()
        },
        "raw_sign_test_p": raw_p,
        "holm_adjusted_p": adjusted,
        "familywise_alpha": 0.05,
        "inferential_unit": "matched_seed_within_fixed_primary_scenario",
    }


def recovery_time(
    pre_windows: Sequence[Mapping[str, float | int]],
    post_windows: Sequence[Mapping[str, float | int]],
    *,
    metric_key: str,
    higher_is_better: bool,
    stream_end_index: int,
) -> dict[str, Any]:
    if len(pre_windows) < 3:
        raise ValueError("At least three pre-drift windows are required.")
    final_three = pre_windows[-3:]
    rows = np.asarray(
        [int(item["row_count"]) for item in final_three],
        dtype=np.float64,
    )
    values = np.asarray(
        [float(item[metric_key]) for item in final_three],
        dtype=np.float64,
    )
    if np.any(rows <= 0):
        raise ValueError("Window row_count must be positive.")
    baseline = float(np.average(values, weights=rows))

    def qualifies(value: float) -> bool:
        return (
            value >= baseline if higher_is_better else value <= baseline
        )

    for index in range(len(post_windows) - 1):
        current = float(post_windows[index][metric_key])
        following = float(post_windows[index + 1][metric_key])
        if qualifies(current) and qualifies(following):
            return {
                "baseline": baseline,
                "recovered": True,
                "recovery_clock": int(post_windows[index]["start_index"]),
                "right_censored": False,
            }

    return {
        "baseline": baseline,
        "recovered": False,
        "recovery_clock": int(stream_end_index),
        "right_censored": True,
    }



def summarize_symbolic_maintenance(
    records: Sequence[Any],
) -> dict[str, Any]:
    opportunities = len(records)
    publications = sum(
        int(record.symbolic_publication_effective_index is not None)
        for record in records
    )
    completed_validation = sum(
        int(bool(record.validation_row_ids))
        for record in records
        if not str(record.status).startswith(
            (
                "right_censored_validation",
                "superseded_before_validation",
                "superseded_before_symbolic_publication",
            )
        )
    )
    no_ops = sum(
        int(str(record.status).startswith("no_rule_base_change"))
        for record in records
    )
    censored = sum(
        int(
            any(
                token in str(record.status)
                for token in (
                    "right_censored",
                    "superseded",
                    "pending_transaction_skip",
                    "insufficient_generation_rows",
                    "blocked_no_executable_neural_child",
                )
            )
        )
        for record in records
    )
    total_shap = float(
        sum(float(getattr(record, "shap_seconds", 0.0)) for record in records)
    )
    total_surrogate = float(
        sum(
            float(getattr(record, "surrogate_seconds", 0.0))
            for record in records
        )
    )
    total_lifecycle = float(
        sum(
            float(getattr(record, "lifecycle_seconds", 0.0))
            for record in records
        )
    )
    candidate_count = int(
        sum(int(getattr(record, "candidate_count", 0)) for record in records)
    )
    wait_rows = [
        int(record.validation_wait_rows)
        for record in records
        if getattr(record, "validation_wait_rows", None) is not None
    ]

    lifecycle_counts: dict[str, int] = {}
    for record in records:
        transaction = getattr(record, "lifecycle", None)
        lifecycle = (
            transaction.lifecycle
            if transaction is not None
            else None
        )
        if lifecycle is None:
            continue
        for decision in lifecycle.decisions:
            name = str(decision["type"])
            lifecycle_counts[name] = lifecycle_counts.get(name, 0) + 1

    compute_seconds = total_shap + total_surrogate + total_lifecycle
    return {
        "opportunity_count": opportunities,
        "completed_validation_count": completed_validation,
        "publication_count": publications,
        "no_op_count": no_ops,
        "censored_or_blocked_count": censored,
        "candidate_count": candidate_count,
        "publication_per_opportunity": (
            publications / opportunities if opportunities else None
        ),
        "compute_seconds": compute_seconds,
        "shap_seconds": total_shap,
        "surrogate_seconds": total_surrogate,
        "lifecycle_seconds": total_lifecycle,
        "compute_seconds_per_opportunity": (
            compute_seconds / opportunities if opportunities else None
        ),
        "compute_seconds_per_publication": (
            compute_seconds / publications if publications else None
        ),
        "mean_validation_wait_rows": (
            float(np.mean(wait_rows)) if wait_rows else None
        ),
        "lifecycle_decision_counts": dict(
            sorted(lifecycle_counts.items())
        ),
    }
