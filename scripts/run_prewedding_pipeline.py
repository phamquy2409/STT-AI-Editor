
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_pipeline import PIPELINE_INTENTS, run_prewedding_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full prewedding AI pipeline: 046 -> 047 -> 048 -> 050 -> 049.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--intent", default="prewedding_reel_60s", choices=PIPELINE_INTENTS)
    parser.add_argument("--preset", default=None)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = run_prewedding_pipeline(
        project_root=args.project,
        intent=args.intent,
        preset=args.preset,
        target_duration=args.duration,
        open_folder=not args.no_open,
        stop_on_error=not args.continue_on_error,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
