from __future__ import annotations

import argparse
import json
import math
import statistics
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tools.stage9_5.claim_traceability import PROJECT_ROOT
from tools.stage9_5.claim_traceability import run as run_claim_traceability
from tools.stage9_5.statistical_oracle import (
    CONTRACT_PATH as ORACLE_CONTRACT_PATH,
)
from tools.stage9_5.statistical_oracle import (
    _explanation_metric,
    _metric_from_counts,
    _stage8_eval,
)
from tools.stage9_5.statistical_oracle import (
    _load_json as load_oracle_json,
)
from tools.stage9_5.statistical_oracle import (
    run as run_statistical_oracle,
)

CONTRACT_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_claim_reporting_v1.json"
TOL = 1e-10


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _claim_index(claim_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["claim_id"]): item for item in claim_report["claims"]}


def _datum(
    claim: Mapping[str, Any],
    value_name: str,
    *,
    subpath: str | None = None,
    authority: str,
) -> dict[str, Any]:
    value = claim["resolved_values"][value_name]
    selector: Any = claim["evidence_selector"][value_name]
    if subpath:
        current = value
        for token in subpath.lstrip("/").split("/"):
            current = current[int(token)] if isinstance(current, list) else current[token]
        value = current
        selector = {"base_selector": selector, "resolved_subpath": subpath}
    return {
        "claim_id": claim["claim_id"],
        "value_name": value_name,
        "evidence_selector": selector,
        "verification_authority": authority,
        "value": value,
    }


def _compare(
    mismatches: list[dict[str, Any]],
    name: str,
    actual: Any,
    expected: Any,
) -> int:
    comparisons = 0
    if isinstance(actual, Mapping) and isinstance(expected, Mapping):
        if set(actual) != set(expected):
            mismatches.append(
                {
                    "name": name,
                    "reason": "mapping_keys",
                    "actual_keys": sorted(actual),
                    "expected_keys": sorted(expected),
                }
            )
            return 1
        for key in sorted(actual):
            comparisons += _compare(mismatches, f"{name}/{key}", actual[key], expected[key])
        return comparisons
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            mismatches.append(
                {
                    "name": name,
                    "reason": "list_length",
                    "actual_length": len(actual),
                    "expected_length": len(expected),
                }
            )
            return 1
        for index, (left, right) in enumerate(zip(actual, expected)):
            comparisons += _compare(mismatches, f"{name}/{index}", left, right)
        return comparisons
    comparisons += 1
    if isinstance(actual, bool) or isinstance(expected, bool):
        if actual is not expected:
            mismatches.append({"name": name, "actual": actual, "expected": expected})
        return comparisons
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=TOL):
            mismatches.append(
                {
                    "name": name,
                    "actual": actual,
                    "expected": expected,
                    "absolute_difference": abs(float(actual) - float(expected)),
                    "tolerance": TOL,
                }
            )
        return comparisons
    if actual != expected:
        mismatches.append({"name": name, "actual": actual, "expected": expected})
    return comparisons


def _primary_arm_oracle_means() -> dict[str, dict[str, float]]:
    contract = load_oracle_json(ORACLE_CONTRACT_PATH)
    result: dict[str, dict[str, float]] = {}
    for arm in ("c_frozen_symbolic", "d_drift", "d_periodic"):
        series: dict[str, list[float]] = {
            key: []
            for key in ("mcc", "f1", "fpr", "mcsc", "resolved_coverage")
        }
        for seed in contract["seeds"]:
            payload = _stage8_eval(contract, int(seed), arm)
            post = payload["metrics_by_neural_weight"]["0.5"]["post"]
            explanation = payload["explanation"]["post"]
            series["mcc"].append(_metric_from_counts("mcc", post))
            series["f1"].append(_metric_from_counts("f1", post))
            series["fpr"].append(_metric_from_counts("fpr", post))
            series["mcsc"].append(_explanation_metric("mcsc", explanation))
            series["resolved_coverage"].append(
                _explanation_metric("resolved_coverage", explanation)
            )
        result[arm] = {name: statistics.fmean(values) for name, values in series.items()}
    return result


def _write_source(path: Path, source_id: str, records: list[dict[str, Any]]) -> None:
    payload = {
        "schema_version": 1,
        "source_id": source_id,
        "rounding_applied": False,
        "records": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    with tempfile.TemporaryDirectory(prefix="stage9_5_reporting_") as temp:
        temp_root = Path(temp)
        claim_report = run_claim_traceability(temp_root / "claims")
        oracle_report = run_statistical_oracle(temp_root / "oracle")

    claims = _claim_index(claim_report)
    mismatches: list[dict[str, Any]] = []
    oracle_comparisons = 0

    # Stage-8 confirmatory family against the independent oracle.
    for endpoint in (
        "E1_post_mcc_d_drift_minus_c",
        "E2_post_mcsc_d_drift_minus_c",
        "E3_post_mcsc_d_drift_minus_d_periodic",
    ):
        claim = claims[f"primary_{endpoint}"]
        accepted = claim["resolved_values"]["summary"]
        oracle_summary = dict(oracle_report["stage8"]["summaries"][endpoint])
        oracle_summary["effects"] = oracle_report["stage8"]["effects"][endpoint]
        oracle_summary.pop("values", None)
        oracle_summary["endpoint"] = endpoint
        oracle_comparisons += _compare(
            mismatches,
            f"primary/{endpoint}/summary",
            accepted,
            oracle_summary,
        )
        oracle_comparisons += _compare(
            mismatches,
            f"primary/{endpoint}/holm",
            claim["resolved_values"]["holm_adjusted_p"],
            oracle_report["stage8"]["holm_adjusted_p"][endpoint],
        )
        oracle_comparisons += _compare(
            mismatches,
            f"primary/{endpoint}/raw_sign",
            claim["resolved_values"]["raw_sign_test_p"],
            oracle_report["stage8"]["raw_sign_test_p"][endpoint],
        )

    # Primary marginal endpoints recomputed with the independent oracle formulas.
    oracle_arm_means = _primary_arm_oracle_means()
    operating = claims["primary_operating_tradeoff"]
    for arm, metrics in oracle_arm_means.items():
        for metric, expected_value in metrics.items():
            key = f"{arm}_{metric}_mean"
            oracle_comparisons += _compare(
                mismatches,
                f"primary_operating/{key}",
                operating["resolved_values"][key],
                expected_value,
            )

    # Stage-9 conditionwise oracle-covered contrasts.
    condition_claims = {
        "robustness_conditionwise_d_drift_minus_c": "d_drift_minus_c",
        "robustness_d_drift_minus_periodic": "d_drift_minus_d_periodic",
    }
    for claim_id, contrast_name in condition_claims.items():
        claim = claims[claim_id]
        mean_map = claim["resolved_values"]["mcc_mean_by_condition"]
        value_map = claim["resolved_values"]["mcc_values_by_condition"]
        for condition, actual_mean in mean_map.items():
            expected = oracle_report["stage9"][condition]["contrasts"][contrast_name]["mcc"]
            oracle_comparisons += _compare(
                mismatches,
                f"stage9/{condition}/{contrast_name}/mcc/mean",
                actual_mean,
                expected["mean"],
            )
            oracle_comparisons += _compare(
                mismatches,
                f"stage9/{condition}/{contrast_name}/mcc/values",
                value_map[condition],
                expected["values"],
            )

    explanation_claim = claims["robustness_explanation_coverage_tradeoff"]
    for metric, key in (
        ("mcsc", "mcsc_mean_by_condition"),
        ("resolved_coverage", "resolved_coverage_mean_by_condition"),
    ):
        for condition, actual_mean in explanation_claim["resolved_values"][key].items():
            expected = oracle_report["stage9"][condition]["contrasts"]["d_drift_minus_c"][metric]
            oracle_comparisons += _compare(
                mismatches,
                f"stage9/{condition}/d_drift_minus_c/{metric}/mean",
                actual_mean,
                expected["mean"],
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "claim_ledger.json").write_text(
        json.dumps(claim_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    primary_confirmatory: list[dict[str, Any]] = []
    for endpoint in (
        "E1_post_mcc_d_drift_minus_c",
        "E2_post_mcsc_d_drift_minus_c",
        "E3_post_mcsc_d_drift_minus_d_periodic",
    ):
        claim = claims[f"primary_{endpoint}"]
        for key in ("summary", "holm_adjusted_p", "raw_sign_test_p"):
            primary_confirmatory.append(
                _datum(claim, key, authority="stage9.5-independent-oracle")
            )

    operating_records = [
        _datum(
            operating,
            key,
            authority=(
                "stage9.5-independent-oracle"
                if any(token in key for token in ("_mcc_", "_f1_", "_fpr_", "_mcsc_", "_resolved_coverage_"))
                else "immutable-evidence-selector"
            ),
        )
        for key in sorted(operating["resolved_values"])
    ]

    mechanism_records: list[dict[str, Any]] = []
    for claim_id in (
        "mechanism_decomposition",
        "mechanism_rescue_harm_counts",
        "mechanism_periodic_context",
    ):
        claim = claims[claim_id]
        mechanism_records.extend(
            _datum(claim, key, authority="immutable-evidence-selector")
            for key in sorted(claim["resolved_values"])
        )

    robustness_records: list[dict[str, Any]] = []
    for claim_id in (
        "robustness_conditionwise_d_drift_minus_c",
        "robustness_lambda1_neural_only",
        "robustness_detector_replay_gate",
        "robustness_d_drift_minus_periodic",
        "robustness_explanation_coverage_tradeoff",
    ):
        claim = claims[claim_id]
        authority = (
            "immutable-evidence-selector"
            if claim_id == "robustness_lambda1_neural_only"
            else "stage9.5-independent-oracle"
        )
        robustness_records.extend(
            _datum(claim, key, authority=authority)
            for key in sorted(claim["resolved_values"])
        )

    timing_records: list[dict[str, Any]] = []
    for claim_id in (
        "primary_publication_timing",
        "primary_maintenance_budget_compute_wait",
        "primary_recovery",
        "robustness_publication_timing",
    ):
        claim = claims[claim_id]
        timing_records.extend(
            _datum(claim, key, authority="immutable-evidence-selector")
            for key in sorted(claim["resolved_values"])
        )

    _write_source(
        output_dir / "tables/primary_confirmatory.json",
        "primary_confirmatory",
        primary_confirmatory,
    )
    _write_source(
        output_dir / "tables/primary_operating_tradeoff.json",
        "primary_operating_tradeoff",
        operating_records,
    )
    _write_source(
        output_dir / "tables/mechanism_decomposition.json",
        "mechanism_decomposition",
        mechanism_records,
    )
    _write_source(
        output_dir / "tables/stage9_robustness.json",
        "stage9_robustness",
        robustness_records,
    )
    _write_source(
        output_dir / "tables/timing_and_recovery.json",
        "timing_and_recovery",
        timing_records,
    )

    primary_figure_records = [
        _datum(
            claims[f"primary_{endpoint}"],
            "summary",
            subpath="/effects",
            authority="stage9.5-independent-oracle",
        )
        for endpoint in (
            "E1_post_mcc_d_drift_minus_c",
            "E2_post_mcsc_d_drift_minus_c",
            "E3_post_mcsc_d_drift_minus_d_periodic",
        )
    ]
    _write_source(
        output_dir / "figures/primary_effects_source.json",
        "primary_effects",
        primary_figure_records,
    )
    _write_source(
        output_dir / "figures/robustness_effects_source.json",
        "robustness_effects",
        [
            _datum(
                claims["robustness_conditionwise_d_drift_minus_c"],
                "mcc_values_by_condition",
                authority="stage9.5-independent-oracle",
            ),
            _datum(
                claims["robustness_d_drift_minus_periodic"],
                "mcc_values_by_condition",
                authority="stage9.5-independent-oracle",
            ),
        ],
    )
    _write_source(
        output_dir / "figures/mechanism_source.json",
        "mechanism",
        [
            _datum(
                claims["mechanism_decomposition"],
                key,
                authority="immutable-evidence-selector",
            )
            for key in sorted(claims["mechanism_decomposition"]["resolved_values"])
        ],
    )

    required = contract["stage9_5_8"]["required_outputs"]
    missing_outputs = [
        relative for relative in required if not (output_dir / relative).is_file()
    ]
    report: dict[str, Any] = {
        "audit_id": "stage9.5-8-independent-table-figure-regeneration-v1",
        "contract": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "claim_ledger_canonical_sha256": claim_report["canonical_sha256"],
        "independent_oracle_canonical_sha256": oracle_report["canonical_sha256"],
        "oracle_comparison_count": oracle_comparisons,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "required_outputs": required,
        "missing_outputs": missing_outputs,
        "production_reporting_imports_used": False,
        "presentation_rounding_applied_to_source_values": False,
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
    }
    report["pass"] = not mismatches and not missing_outputs
    report["status"] = "pass" if report["pass"] else "blocked"
    report["canonical_sha256"] = __import__("hashlib").sha256(
        json.dumps(
            {key: value for key, value in report.items() if key != "canonical_sha256"},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    (output_dir / "reporting_assurance_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not report["pass"]:
        raise SystemExit(
            f"Stage 9.5-8 blocked: mismatches={len(mismatches)}, missing_outputs={missing_outputs}"
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate Stage 9.5-8 table/figure source data independently"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_reporting_v1"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
