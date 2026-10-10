from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def _bootstrap_src() -> None:
    value = str(SRC)
    if value not in sys.path:
        sys.path.insert(0, value)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage-9 prespecified robustness runner."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--verify", action="store_true")

    phase_a = sub.add_parser("phase-a")
    phase_a.add_argument("--condition", required=True)
    phase_a.add_argument("--seed", required=True, type=int)
    phase_a.add_argument("--verify-only", action="store_true")

    symbolic = sub.add_parser("symbolic")
    symbolic.add_argument("--condition", required=True)
    symbolic.add_argument("--seed", required=True, type=int)
    symbolic.add_argument("--verify-only", action="store_true")

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--condition", required=True)
    evaluate.add_argument("--seed", required=True, type=int)
    evaluate.add_argument("--verify-only", action="store_true")

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--condition", required=True)
    aggregate.add_argument("--verify-only", action="store_true")

    export = sub.add_parser("export")
    export.add_argument("--verify-only", action="store_true")

    args = parser.parse_args()
    _bootstrap_src()

    if args.command == "prepare":
        from concept_drift_ids.cd_stage9_config import (
            load_stage9_config,
            verify_stage9_config_for_execution,
            write_stage9_config,
        )

        if args.verify:
            payload = verify_stage9_config_for_execution()
            print(
                __import__("json").dumps(
                    {
                        "status": "stage9_config_verified_for_execution",
                        "manifest_sha256": payload["manifest_sha256"],
                        "source_commit": payload["source_commit"],
                        "matched_stage9_baseline_required": payload["runtime"][
                            "comparison"
                        ]["matched_stage9_baseline_required"],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            payload = write_stage9_config()
            print(
                __import__("json").dumps(
                    {
                        "status": "stage9_config_written_pre_outcome",
                        "manifest_sha256": payload["manifest_sha256"],
                        "source_commit": payload["source_commit"],
                        "matched_stage9_baseline_required": payload["runtime"][
                            "comparison"
                        ]["matched_stage9_baseline_required"],
                        "primary_partitions_loaded": False,
                        "heavy_phase_c_traces_loaded": False,
                        "stage9_outcome_accessed": False,
                        "next_gate": (
                            "commit only data/manifests/cd_stage9_run_config_v1.json "
                            "and require exact-head CI"
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        return

    if args.command == "phase-a":
        from concept_drift_ids.cd_stage9_phase_a import (
            execute_stage9_phase_a_seed,
            verify_stage9_phase_a_seed,
        )

        result = (
            verify_stage9_phase_a_seed(args.condition, args.seed)
            if args.verify_only
            else execute_stage9_phase_a_seed(args.condition, args.seed)
        )
    elif args.command == "symbolic":
        from concept_drift_ids.cd_stage9_symbolic import (
            execute_stage9_symbolic_seed,
            verify_stage9_symbolic_seed,
        )

        result = (
            verify_stage9_symbolic_seed(args.condition, args.seed)
            if args.verify_only
            else execute_stage9_symbolic_seed(args.condition, args.seed)
        )
    elif args.command == "evaluate":
        from concept_drift_ids.cd_stage9_evaluation import (
            execute_stage9_evaluation_seed,
            verify_stage9_evaluation_seed,
        )

        result = (
            verify_stage9_evaluation_seed(args.condition, args.seed)
            if args.verify_only
            else execute_stage9_evaluation_seed(args.condition, args.seed)
        )
    elif args.command == "aggregate":
        from concept_drift_ids.cd_stage9_evaluation import (
            build_stage9_condition_aggregate,
            verify_stage9_condition_aggregate,
        )

        result = (
            verify_stage9_condition_aggregate(args.condition)
            if args.verify_only
            else build_stage9_condition_aggregate(args.condition)
        )
    else:
        from concept_drift_ids.cd_stage9_export import (
            export_stage9_compact_evidence,
            verify_stage9_compact_evidence,
        )

        result = (
            verify_stage9_compact_evidence()
            if args.verify_only
            else export_stage9_compact_evidence()
        )

    print(__import__("json").dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
