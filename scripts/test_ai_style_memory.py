
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_style_memory import AIStyleMemoryV2


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    memory = AIStyleMemoryV2(project_root)

    print("Module 045 AI Style Memory V2 import OK.")
    print("Project:", project_root)
    print("Project memory:", memory.project_memory_path)
    print("AppData memory:", memory.appdata_memory_path)
    print()
    print("Build memory:")
    print("python scripts/build_ai_style_memory.py")


if __name__ == "__main__":
    main()
