from __future__ import annotations

import argparse
import hashlib
import json
import math
from math import comb
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Iterable, Mapping, Sequence

from scipy.stats import t as student_t


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_statistical_oracle_v1.json"
TOL = 1e-10
EXACT_TOL = 1e-12
METRICS = ("mcc", "f1", "fpr", "mcsc", "resolved_coverage")
ARMS = ("c_frozen_symbolic", "d_drift", "d_periodic")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_sha256(payload: Any) -> str:
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


def _metric_from_counts(metric: str, counts: Mapping[str, Any]) -> float:
    tp = int(counts["tp"])
    tn = int(counts["tn"])
    fp = int(counts["fp"])
    fn = int(counts["fn"])
    if metric == "f1":
        denom = 2 * tp + fp + fn
        return (2.0 * tp / denom) if denom else 0.0
    if metric == "fpr":
        denom = fp + tn
        return (fp / denom) if denom else 0.0
    if metric == "mcc":
        denom = math.sqrt(
            (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
        )
        return ((tp * tn - fp * fn) / denom) if denom else 0.0
    raise ValueError(f"Unsupported count-derived metric: {metric}")


def _explanation_metric(metric: str, explanation: Mapping[str, Any]) -> float:
    if metric == "mcsc":
        return 0.5 * (
            float(explanation["attack_correct_symbolic_coverage"])
            + float(explanation["benign_correct_symbolic_coverage"])
        )
    if metric == "resolved_coverage":
        return (
            1.0
            - float(explanation["uncovered_rate"])
            - float(explanation["conflict_abstain_rate"])
        )
    raise ValueError(f"Unsupported explanation metric: {metric}")


def _describe(values: Sequence[float]) -> dict[str, Any]:
    vals = [float(v) for v in values]
    if not vals:
        raise ValueError("Cannot summarize an empty sequence.")
    avg = mean(vals)
    sd = stdev(vals) if len(vals) > 1 else 0.0
    loo = [
        mean(vals[:i] + vals[i + 1 :])
        for i in range(len(vals))
        if len(vals) > 1
    ]
    if len(vals) > 1:
        critical = float(student_t.ppf(0.975, df=len(vals) - 1))
        half = critical * sd / math.sqrt(len(vals))
        interval = [avg - half, avg + half]
    else:
        interval = [avg, avg]
    return {
        "values": vals,
        "mean": avg,
        "median": median(vals),
        "sample_sd": sd,
        "minimum": min(vals),
        "maximum": max(vals),
        "positive": sum(v > 0 for v in vals),
        "negative": sum(v < 0 for v in vals),
        "zero": sum(v == 0 for v in vals),
        "leave_one_seed_out_mean_range": (
            [min(loo), max(loo)] if loo else [avg, avg]
        ),
        "t95_interval_descriptive": interval,
    }


def _stage8_describe(values: Sequence[float]) -> dict[str, Any]:
    base = _describe(values)
    lo, hi = base.pop("leave_one_seed_out_mean_range")
    ci_lo, ci_hi = base.pop("t95_interval_descriptive")
    base["leave_one_seed_out_mean_min"] = lo
    base["leave_one_seed_out_mean_max"] = hi
    base["ci95_low"] = ci_lo
    base["ci95_high"] = ci_hi
    return base


def _sign_test_greater(values: Sequence[float]) -> dict[str, Any]:
    nonzero = [float(v) for v in values if float(v) != 0.0]
    positives = sum(v > 0 for v in nonzero)
    n = len(nonzero)
    if n == 0:
        p = 1.0
    else:
        p = sum(comb(n, k) for k in range(positives, n + 1)) / (2**n)
    return {
        "sign_test_n_effective": n,
        "sign_test_positive": positives,
        "sign_test_p_one_sided": float(p),
    }


def _holm_adjust(raw: Mapping[str, float], order: Sequence[str]) -> dict[str, float]:
    indexed = [(name, float(raw[name]), order.index(name)) for name in order]
    ranked = sorted(indexed, key=lambda row: (row[1], row[2]))
    m = len(ranked)
    running = 0.0
    adjusted: dict[str, float] = {}
    for rank, (name, p, _) in enumerate(ranked, start=1):
        candidate = min(1.0, (m - rank + 1) * p)
        running = max(running, candidate)
        adjusted[name] = min(1.0, running)
    return {name: adjusted[name] for name in order}


def _record_numeric(
    report: dict[str, Any],
    name: str,
    actual: float,
    expected: float,
    *,
    tolerance: float = TOL,
) -> None:
    diff = abs(float(actual) - float(expected))
    report["comparison_count"] += 1
    if diff > tolerance:
        report["mismatches"].append(
            {
                "name": name,
                "actual": float(actual),
                "expected": float(expected),
                "absolute_difference": diff,
                "tolerance": tolerance,
            }
        )


def _jsonable(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(_jsonable(v) for v in value)
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def _record_exact(report: dict[str, Any], name: str, actual: Any, expected: Any) -> None:
    report["comparison_count"] += 1
    if actual != expected:
        report["mismatches"].append(
            {
                "name": name,
                "actual": _jsonable(actual),
                "expected": _jsonable(expected),
                "comparison": "exact",
            }
        )


def _compare_summary(
    report: dict[str, Any],
    prefix: str,
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    stage8: bool = False,
) -> None:
    exact_keys = ("positive", "negative", "zero")
    for key in exact_keys:
        _record_exact(report, f"{prefix}.{key}", actual[key], expected[key])
    for key in ("values",):
        _record_exact(report, f"{prefix}.{key}.length", len(actual[key]), len(expected[key]))
        for i, (a, e) in enumerate(zip(actual[key], expected[key])):
            _record_numeric(report, f"{prefix}.{key}[{i}]", a, e)
    numeric_keys = ("mean", "median", "sample_sd", "minimum", "maximum")
    for key in numeric_keys:
        _record_numeric(report, f"{prefix}.{key}", actual[key], expected[key])
    if stage8:
        for key in (
            "leave_one_seed_out_mean_min",
            "leave_one_seed_out_mean_max",
            "ci95_low",
            "ci95_high",
        ):
            _record_numeric(report, f"{prefix}.{key}", actual[key], expected[key])
    else:
        for key in ("leave_one_seed_out_mean_range", "t95_interval_descriptive"):
            _record_exact(report, f"{prefix}.{key}.length", len(actual[key]), len(expected[key]))
            for i, (a, e) in enumerate(zip(actual[key], expected[key])):
                _record_numeric(report, f"{prefix}.{key}[{i}]", a, e)


def _stage8_eval(contract: Mapping[str, Any], seed: int, arm: str) -> dict[str, Any]:
    path = PROJECT_ROOT / contract["stage8"]["evaluation_pattern"].format(seed=seed, arm=arm)
    return _load_json(path)


def _stage8_endpoint_values(
    report: dict[str, Any],
    contract: Mapping[str, Any],
) -> tuple[dict[str, dict[str, float]], dict[str, list[float]]]:
    seeds = [int(v) for v in contract["seeds"]]
    per_seed: dict[str, dict[str, float]] = {}
    effects: dict[str, list[float]] = {
        endpoint: [] for endpoint in contract["stage8"]["endpoints"]
    }
    endpoint_specs = contract["stage8"]["endpoints"]
    for seed in seeds:
        arm_values: dict[str, dict[str, float]] = {}
        for arm in ARMS:
            payload = _stage8_eval(contract, seed, arm)
            post = payload["metrics_by_neural_weight"]["0.5"]["post"]
            expl = payload["explanation"]["post"]
            values = {
                "mcc": _metric_from_counts("mcc", post),
                "f1": _metric_from_counts("f1", post),
                "fpr": _metric_from_counts("fpr", post),
                "mcsc": _explanation_metric("mcsc", expl),
                "resolved_coverage": _explanation_metric("resolved_coverage", expl),
            }
            for metric in METRICS:
                stored = (
                    post[metric]
                    if metric in ("mcc", "f1", "fpr")
                    else expl[metric]
                )
                _record_numeric(
                    report,
                    f"stage8.seed{seed}.{arm}.{metric}.primitive_vs_stored",
                    values[metric],
                    stored,
                )
            arm_values[arm] = values
        per_seed[str(seed)] = {
            f"{arm}.{metric}": value
            for arm, metrics in arm_values.items()
            for metric, value in metrics.items()
        }
        for endpoint, spec in endpoint_specs.items():
            left_arm, left_metric = spec["left"]
            right_arm, right_metric = spec["right"]
            effects[endpoint].append(
                arm_values[left_arm][left_metric] - arm_values[right_arm][right_metric]
            )
    return per_seed, effects


def _verify_stage8(report: dict[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    _, effects = _stage8_endpoint_values(report, contract)
    confirmatory = _load_json(PROJECT_ROOT / contract["stage8"]["confirmatory_path"])
    _record_exact(
        report,
        "stage8.confirmatory_manifest_sha256",
        confirmatory.get("manifest_sha256"),
        contract["stage8"]["confirmatory_manifest_sha256"],
    )
    authority = confirmatory["confirmatory_family"]
    raw_p: dict[str, float] = {}
    oracle_summaries: dict[str, Any] = {}
    for endpoint, values in effects.items():
        summary = _stage8_describe(values)
        sign = _sign_test_greater(values)
        summary.update(sign)
        raw_p[endpoint] = float(sign["sign_test_p_one_sided"])
        expected = authority["summaries"][endpoint]
        _compare_summary(report, f"stage8.{endpoint}", summary, expected, stage8=True)
        for key in ("sign_test_n_effective", "sign_test_positive"):
            _record_exact(report, f"stage8.{endpoint}.{key}", summary[key], expected[key])
        _record_numeric(
            report,
            f"stage8.{endpoint}.sign_test_p_one_sided",
            summary["sign_test_p_one_sided"],
            expected["sign_test_p_one_sided"],
            tolerance=EXACT_TOL,
        )
        _record_numeric(
            report,
            f"stage8.{endpoint}.raw_sign_test_p",
            raw_p[endpoint],
            authority["raw_sign_test_p"][endpoint],
            tolerance=EXACT_TOL,
        )
        oracle_summaries[endpoint] = summary

    order = list(authority["endpoint_order"])
    adjusted = _holm_adjust(raw_p, order)
    for endpoint in order:
        _record_numeric(
            report,
            f"stage8.{endpoint}.holm_adjusted_p",
            adjusted[endpoint],
            authority["holm_adjusted_p"][endpoint],
            tolerance=EXACT_TOL,
        )
    return {
        "effects": effects,
        "summaries": oracle_summaries,
        "raw_sign_test_p": raw_p,
        "holm_adjusted_p": adjusted,
    }


def _stage9_scored_values(
    report: dict[str, Any],
    contract: Mapping[str, Any],
    condition: str,
) -> dict[str, dict[str, list[float]]]:
    values = {arm: {metric: [] for metric in METRICS} for arm in ARMS}
    for seed in contract["seeds"]:
        for arm in ARMS:
            path = PROJECT_ROOT / contract["stage9"]["scored_pattern"].format(
                condition=condition, seed=seed, arm=arm
            )
            payload = _load_json(path)
            post = payload["metrics_by_neural_weight"]["0.5"]["post"]
            expl = payload["explanation"]["post"]
            computed = {
                "mcc": _metric_from_counts("mcc", post),
                "f1": _metric_from_counts("f1", post),
                "fpr": _metric_from_counts("fpr", post),
                "mcsc": _explanation_metric("mcsc", expl),
                "resolved_coverage": _explanation_metric("resolved_coverage", expl),
            }
            for metric, value in computed.items():
                stored = post[metric] if metric in ("mcc", "f1", "fpr") else expl[metric]
                _record_numeric(
                    report,
                    f"stage9.{condition}.seed{seed}.{arm}.{metric}.primitive_vs_stored",
                    value,
                    stored,
                )
                values[arm][metric].append(value)
    return values


def _stage9_offline_lambda_values(
    report: dict[str, Any],
    contract: Mapping[str, Any],
    condition: str,
) -> dict[str, dict[str, list[float]]]:
    values = {arm: {metric: [] for metric in METRICS} for arm in ARMS}
    for seed in contract["seeds"]:
        path = PROJECT_ROOT / contract["stage9"]["offline_pattern"].format(
            condition=condition, seed=seed
        )
        payload = _load_json(path)
        for arm in ARMS:
            post = payload["results"][arm]["metrics"]["post"]
            stage8 = _stage8_eval(contract, int(seed), arm)
            expl = stage8["explanation"]["post"]
            computed = {
                "mcc": _metric_from_counts("mcc", post),
                "f1": _metric_from_counts("f1", post),
                "fpr": _metric_from_counts("fpr", post),
                "mcsc": _explanation_metric("mcsc", expl),
                "resolved_coverage": _explanation_metric("resolved_coverage", expl),
            }
            for metric, value in computed.items():
                if metric in ("mcc", "f1", "fpr"):
                    _record_numeric(
                        report,
                        f"stage9.{condition}.seed{seed}.{arm}.{metric}.primitive_vs_stored",
                        value,
                        post[metric],
                    )
                values[arm][metric].append(value)
    return values


def _compare_stage9_arm_and_contrast_summaries(
    report: dict[str, Any],
    condition: str,
    values: Mapping[str, Mapping[str, Sequence[float]]],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    oracle: dict[str, Any] = {"arms": {}, "contrasts": {}}
    for arm in ARMS:
        oracle["arms"][arm] = {}
        for metric in METRICS:
            summary = _describe(values[arm][metric])
            oracle["arms"][arm][metric] = summary
            _compare_summary(
                report,
                f"stage9.{condition}.arms.{arm}.{metric}",
                summary,
                authority["arms"][arm][metric],
            )
    contrast_specs = {
        "d_drift_minus_c": ("d_drift", "c_frozen_symbolic"),
        "d_drift_minus_d_periodic": ("d_drift", "d_periodic"),
        "d_periodic_minus_c": ("d_periodic", "c_frozen_symbolic"),
    }
    for name, (left, right) in contrast_specs.items():
        oracle["contrasts"][name] = {}
        for metric in METRICS:
            diffs = [
                float(a) - float(b)
                for a, b in zip(values[left][metric], values[right][metric])
            ]
            summary = _describe(diffs)
            oracle["contrasts"][name][metric] = summary
            _compare_summary(
                report,
                f"stage9.{condition}.contrasts.{name}.{metric}",
                summary,
                authority["within_condition_primary_contrasts"][name][metric],
            )
    return oracle


def _compare_recovery_record(
    report: dict[str, Any],
    prefix: str,
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    for key in ("available", "recovered", "right_censored", "recovery_clock", "recovery_rows_from_boundary"):
        _record_exact(report, f"{prefix}.{key}", actual.get(key), expected.get(key))
    _record_numeric(
        report,
        f"{prefix}.baseline",
        float(actual["baseline"]),
        float(expected["baseline"]),
    )


def _optional_describe(values: Iterable[float]) -> dict[str, Any] | None:
    vals = [float(v) for v in values]
    return _describe(vals) if vals else None


def _compare_optional_summary(
    report: dict[str, Any],
    prefix: str,
    actual: Mapping[str, Any] | None,
    expected: Mapping[str, Any] | None,
) -> None:
    _record_exact(report, f"{prefix}.is_none", actual is None, expected is None)
    if actual is not None and expected is not None:
        _compare_summary(report, prefix, actual, expected)


def _verify_window_condition(
    report: dict[str, Any],
    contract: Mapping[str, Any],
    condition: str,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    _record_exact(
        report,
        f"stage9.{condition}.whole_post_endpoints_changed",
        authority.get("whole_post_endpoints_changed"),
        False,
    )
    expected_window = 10000 if condition == "window_10000" else 2500
    _record_exact(
        report,
        f"stage9.{condition}.reporting_window_rows",
        authority.get("reporting_window_rows"),
        expected_window,
    )
    oracle: dict[str, Any] = {"recovery": {}}
    for arm in ARMS:
        oracle["recovery"][arm] = {}
        primary_records = {
            int(seed): _stage8_eval(contract, int(seed), arm)["primary_recovery"]
            for seed in contract["seeds"]
        }
        alternative_records: dict[int, Any] = {}
        for seed in contract["seeds"]:
            path = PROJECT_ROOT / contract["stage9"]["offline_pattern"].format(
                condition=condition, seed=seed
            )
            payload = _load_json(path)
            alternative_records[int(seed)] = payload["results"][arm]["recovery"]

        for metric in ("fpr", "mcc", "mcsc"):
            expected_metric = authority["recovery"][arm][metric]
            alternatives = {
                seed: alternative_records[seed][metric]
                for seed in sorted(alternative_records)
            }
            primaries = {
                seed: primary_records[seed][metric]
                for seed in sorted(primary_records)
            }
            per_seed_expected = {
                int(row["seed"]): row for row in expected_metric["per_seed"]
            }
            for seed in sorted(alternatives):
                _compare_recovery_record(
                    report,
                    f"stage9.{condition}.{arm}.{metric}.seed{seed}.alternative",
                    alternatives[seed],
                    per_seed_expected[seed]["alternative"],
                )
                _compare_recovery_record(
                    report,
                    f"stage9.{condition}.{arm}.{metric}.seed{seed}.primary5000",
                    primaries[seed],
                    per_seed_expected[seed]["primary_window_5000"],
                )

            available = [r for r in alternatives.values() if r["available"]]
            recovered = [r for r in available if r["recovered"]]
            censored = [r for r in available if r["right_censored"]]
            _record_exact(report, f"stage9.{condition}.{arm}.{metric}.available_count", len(available), expected_metric["available_count"])
            _record_exact(report, f"stage9.{condition}.{arm}.{metric}.recovered_count", len(recovered), expected_metric["recovered_count"])
            _record_exact(report, f"stage9.{condition}.{arm}.{metric}.right_censored_count", len(censored), expected_metric["right_censored_count"])

            observed_summary = _optional_describe(
                r["recovery_rows_from_boundary"] for r in recovered
            )
            _compare_optional_summary(
                report,
                f"stage9.{condition}.{arm}.{metric}.observed_recovery_rows_summary",
                observed_summary,
                expected_metric["observed_recovery_rows_summary"],
            )

            primary_recovered = [r for r in primaries.values() if r["available"] and r["recovered"]]
            primary_summary = _optional_describe(
                r["recovery_rows_from_boundary"] for r in primary_recovered
            )
            _compare_optional_summary(
                report,
                f"stage9.{condition}.{arm}.{metric}.primary5000_observed_recovery_rows_summary",
                primary_summary,
                expected_metric["primary_5000_observed_recovery_rows_summary"],
            )

            paired = []
            for seed in sorted(alternatives):
                alt = alternatives[seed]
                pri = primaries[seed]
                if alt["available"] and alt["recovered"] and pri["available"] and pri["recovered"]:
                    paired.append(
                        float(alt["recovery_rows_from_boundary"])
                        - float(pri["recovery_rows_from_boundary"])
                    )
            paired_summary = _optional_describe(paired)
            _compare_optional_summary(
                report,
                f"stage9.{condition}.{arm}.{metric}.paired_delta_vs_5000",
                paired_summary,
                expected_metric["paired_observed_recovery_row_delta_vs_5000"],
            )
            oracle["recovery"][arm][metric] = {
                "available_count": len(available),
                "recovered_count": len(recovered),
                "right_censored_count": len(censored),
                "observed_recovery_rows_summary": observed_summary,
                "primary_5000_observed_recovery_rows_summary": primary_summary,
                "paired_observed_recovery_row_delta_vs_5000": paired_summary,
            }
    return oracle


def _verify_stage9(report: dict[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    aggregate_path = PROJECT_ROOT / contract["stage9"]["aggregate_path"]
    aggregate = _load_json(aggregate_path)
    _record_exact(
        report,
        "stage9.aggregate_canonical_sha256",
        aggregate.get("aggregate_sha256"),
        contract["stage9"]["aggregate_canonical_sha256"],
    )
    _record_exact(
        report,
        "stage9.execution_plan_sha256",
        aggregate.get("execution_plan_sha256"),
        contract["stage9"]["execution_plan_sha256"],
    )
    conditions = aggregate["conditions"]
    expected_conditions = set(contract["stage9"]["offline_conditions"]) | set(contract["stage9"]["scored_conditions"])
    _record_exact(report, "stage9.condition_set", set(conditions), expected_conditions)
    oracle: dict[str, Any] = {}
    for condition in contract["stage9"]["scored_conditions"]:
        values = _stage9_scored_values(report, contract, condition)
        oracle[condition] = _compare_stage9_arm_and_contrast_summaries(
            report, condition, values, conditions[condition]
        )
    for condition in ("lambda_0_7", "lambda_0_9", "lambda_1_0"):
        values = _stage9_offline_lambda_values(report, contract, condition)
        oracle[condition] = _compare_stage9_arm_and_contrast_summaries(
            report, condition, values, conditions[condition]
        )
    for condition in ("window_10000", "window_2500"):
        oracle[condition] = _verify_window_condition(
            report, contract, condition, conditions[condition]
        )
    return oracle


def run(output_dir: Path) -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    report: dict[str, Any] = {
        "audit_id": "stage9.5-2-independent-statistical-oracle-v1",
        "contract": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "production_aggregation_imports_used": False,
        "comparison_count": 0,
        "mismatches": [],
        "stage8": None,
        "stage9": None,
    }
    report["stage8"] = _verify_stage8(report, contract)
    report["stage9"] = _verify_stage9(report, contract)
    report["mismatch_count"] = len(report["mismatches"])
    report["pass"] = report["mismatch_count"] == 0
    report["status"] = "pass" if report["pass"] else "blocked"
    report["canonical_sha256"] = _canonical_sha256(
        {k: v for k, v in report.items() if k != "canonical_sha256"}
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "statistical_oracle_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage 9.5-2 Independent Statistical Oracle",
        "",
        f"- status: **{report['status'].upper()}**",
        f"- comparisons: **{report['comparison_count']}**",
        f"- mismatches: **{report['mismatch_count']}**",
        f"- report canonical SHA-256: `{report['canonical_sha256']}`",
        "",
        "## Mismatches",
        "",
    ]
    if report["mismatches"]:
        for item in report["mismatches"][:100]:
            lines.append(f"- `{item['name']}`")
    else:
        lines.append("- none")
    (output_dir / "STATISTICAL_ORACLE_REPORT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    if not report["pass"]:
        raise SystemExit(
            f"Stage 9.5-2 blocked: {report['mismatch_count']} discrepancies across "
            f"{report['comparison_count']} comparisons."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Independent Stage 9.5-2 statistical oracle")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_v1/statistical_oracle"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
