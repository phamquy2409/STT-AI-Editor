
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_refiner import REFINER_RULES, PreweddingSmartRefiner


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    refiner = PreweddingSmartRefiner(project_root)

    print("Module 050 Prewedding Smart Refiner import OK.")
    print("Project:", project_root)
    print("Input file:", refiner.find_input_file())
    print("Project refined:", refiner.project_refined_path)
    print("AppData refined:", refiner.appdata_refined_path)
    print()
    print("Refiner intents:")
    for key in sorted(REFINER_RULES):
        print("-", key)
    print()
    print("Run:")
    print("python scripts/refine_prewedding_roughcut.py --intent prewedding_reel_60s")


if __name__ == "__main__":
    main()
