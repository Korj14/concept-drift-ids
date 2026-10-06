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
        choices=("stage3a-preprocess",),
        help="Project command to execute.",
    )
    args = parser.parse_args()

    _bootstrap_src()

    if args.command == "stage3a-preprocess":
        from concept_drift_ids.model_preprocessing import main as run_stage3a

        run_stage3a()


if __name__ == "__main__":
    main()
