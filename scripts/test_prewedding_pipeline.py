
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_pipeline import PIPELINE_INTENTS, PreweddingOneClickPipeline


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    runner = PreweddingOneClickPipeline(project_root)

    print("Module 051 Prewedding One-Click Pipeline import OK.")
    print("Project:", project_root)
    print("Pipeline JSON:", runner.project_pipeline_path)
    print("AppData Pipeline JSON:", runner.appdata_pipeline_path)
    print()
    print("Pipeline intents:")
    for key in PIPELINE_INTENTS:
        print("-", key)
    print()
    print("Run full pipeline:")
    print("python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s")


if __name__ == "__main__":
    main()
