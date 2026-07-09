
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_shot_scorer import AIShotScorerV1, ALL_INTENTS, PREWEDDING_INTENTS


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    scorer = AIShotScorerV1(project_root)

    print("Module 046 AI Shot Scorer V1 import OK.")
    print("Project:", project_root)
    print("Project score path:", scorer.project_score_path)
    print("AppData score path:", scorer.appdata_score_path)
    print()
    print("Prewedding intents:")
    for key in sorted(PREWEDDING_INTENTS):
        print("-", key)
    print()
    print("All intents:")
    for key in sorted(ALL_INTENTS):
        print("-", key)
    print()
    print("Run scorer:")
    print("python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s")


if __name__ == "__main__":
    main()
