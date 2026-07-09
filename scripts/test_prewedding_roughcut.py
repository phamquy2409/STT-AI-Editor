
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_roughcut import ROUGHCUT_RULES, PreweddingRoughcutBuilder


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    builder = PreweddingRoughcutBuilder(project_root)

    print("Module 048 Prewedding Roughcut Builder import OK.")
    print("Project:", project_root)
    print("Selection:", builder.find_selection_file())
    print("Project roughcut:", builder.project_roughcut_path)
    print("AppData roughcut:", builder.appdata_roughcut_path)
    print()
    print("Roughcut intents:")
    for key in sorted(ROUGHCUT_RULES):
        print("-", key)
    print()
    print("Run:")
    print("python scripts/build_prewedding_roughcut.py --intent prewedding_reel_60s")


if __name__ == "__main__":
    main()
