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
        choices=("stage3a-preprocess", "system-a", "system-b", "cd-preflight"),
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

    from concept_drift_ids.cd_implementation_preflight import (
        main as run_cd_preflight,
    )
    run_cd_preflight()


if __name__ == "__main__":
    main()
