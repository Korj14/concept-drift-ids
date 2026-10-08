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
    parser = argparse.ArgumentParser(
        description="Portable project runner for the Concept-Drift IDS repository."
    )
    parser.add_argument(
        "command",
        choices=(
            "stage3a-preprocess",
            "system-a",
            "system-b",
            "cd-preflight",
            "cd-primary-prepare",
            "cd-primary-phase-a",
            "cd-primary-phase-b",
            "cd-primary-phase-c",
            "cd-primary-export",
        ),
        help="Project command to execute.",
    )
    args, remainder = parser.parse_known_args()

    _bootstrap_src()

    if args.command == "stage3a-preprocess":
        if remainder:
            parser.error("stage3a-preprocess takes no additional arguments.")
        from concept_drift_ids.model_preprocessing import main as run_stage3a
        run_stage3a()
        return

    sys.argv = [sys.argv[0], *remainder]

    if args.command == "system-a":
        from concept_drift_ids.system_a import main as run_system_a
        run_system_a()
        return

    if args.command == "system-b":
        from concept_drift_ids.system_b import main as run_system_b
        run_system_b()
        return

    if args.command == "cd-preflight":
        if remainder:
            parser.error("cd-preflight takes no additional arguments.")
        from concept_drift_ids.cd_implementation_preflight import (
            main as run_cd_preflight,
        )
        run_cd_preflight()
        return

    if args.command == "cd-primary-prepare":
        if remainder:
            parser.error("cd-primary-prepare takes no additional arguments.")
        from concept_drift_ids.cd_primary_config import (
            main as run_cd_primary_prepare,
        )
        run_cd_primary_prepare()
        return

    if args.command == "cd-primary-phase-a":
        from concept_drift_ids.cd_primary_phase_a import main as run_phase_a
        run_phase_a()
        return

    if args.command == "cd-primary-phase-b":
        from concept_drift_ids.cd_primary_phase_b import main as run_phase_b
        run_phase_b()
        return

    if args.command == "cd-primary-phase-c":
        from concept_drift_ids.cd_primary_phase_c import main as run_phase_c
        run_phase_c()
        return

    from concept_drift_ids.cd_primary_export import main as run_primary_export
    run_primary_export()


if __name__ == "__main__":
    main()
