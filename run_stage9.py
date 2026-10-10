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
