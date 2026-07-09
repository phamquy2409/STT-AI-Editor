
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_selector import PREWEDDING_TARGETS, build_prewedding_selection


def main() -> None:
    parser = argparse.ArgumentParser(description="Build prewedding learned selection.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--intent", default="prewedding_reel_60s", choices=sorted(PREWEDDING_TARGETS))
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = build_prewedding_selection(
        project_root=args.project,
        intent=args.intent,
        target_duration=args.duration,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
