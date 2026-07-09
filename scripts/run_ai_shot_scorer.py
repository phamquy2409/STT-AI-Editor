
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_shot_scorer import ALL_INTENTS, run_ai_shot_scorer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STT AI Shot Scorer V1.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--intent", default="prewedding_reel_60s", choices=sorted(ALL_INTENTS))
    parser.add_argument("--top-n", type=int, default=120)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = run_ai_shot_scorer(
        project_root=args.project,
        intent=args.intent,
        top_n=args.top_n,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
