
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_selector import PREWEDDING_TARGETS, PreweddingLearnedSelector


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    selector = PreweddingLearnedSelector(project_root)

    print("Module 047 Prewedding Learned Selector import OK.")
    print("Project:", project_root)
    print("Selection path:", selector.project_selection_path)
    print("AppData selection:", selector.appdata_selection_path)
    print()
    print("Available prewedding intents:")
    for key in sorted(PREWEDDING_TARGETS):
        print("-", key)
    print()
    print("Run:")
    print("python scripts/build_prewedding_selection.py --intent prewedding_reel_60s")


if __name__ == "__main__":
    main()
