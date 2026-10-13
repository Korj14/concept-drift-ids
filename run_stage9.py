from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def _bootstrap_src() -> None:
    src = str(SRC)
    if src not in sys.path:
        sys.path.insert(0, src)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage-9 robustness runner.")
    parser.add_argument(
        "command",
        choices=(
            "prepare",
            "verify-config",
            "offline",
            "phase-a",
            "phase-b",
            "phase-c",
            "execute-all",
            "export",
        ),
    )
    args, remainder = parser.parse_known_args()
    _bootstrap_src()
    sys.argv = [sys.argv[0], *remainder]

    if args.command == "prepare":
        if remainder:
            parser.error("prepare takes no additional arguments")
        from concept_drift_ids.cd_stage9_config import main as run
        run()
        return
    if args.command == "verify-config":
        if remainder:
            parser.error("verify-config takes no additional arguments")
        import json
        from concept_drift_ids.cd_stage9_config import (
            verify_stage9_config_for_execution,
        )
        config = verify_stage9_config_for_execution()
        print(
            json.dumps(
                {
                    "status": "stage9_config_verified",
                    "manifest_sha256": config["manifest_sha256"],
                    "prepared_from_git_commit": config[
                        "prepared_from_git_commit"
                    ],
                    "matched_baseline_required": config[
                        "matched_baseline_required"
                    ],
                    "historical_v1_execution": config[
                        "historical_v1_execution"
                    ],
                },
                sort_keys=True,
                indent=2,
            )
        )
        return
    if args.command == "offline":
        from concept_drift_ids.cd_stage9_offline import main as run
        run()
        return
    if args.command == "phase-a":
        from concept_drift_ids.cd_stage9_phase_a import main as run
        run()
        return
    if args.command == "phase-b":
        from concept_drift_ids.cd_stage9_phase_b import main as run
        run()
        return
    if args.command == "phase-c":
        from concept_drift_ids.cd_stage9_phase_c import main as run
        run()
        return
    if args.command == "execute-all":
        from concept_drift_ids.cd_stage9_execute import main as run
        run()
        return

    from concept_drift_ids.cd_stage9_export import main as run
    run()


if __name__ == "__main__":
    main()
