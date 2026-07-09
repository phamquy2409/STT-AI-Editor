from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.shot_detection import detect_shots_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    result = detect_shots_existing_project(
        project_root=project_root,
        segment_seconds=3.0,
        reset_existing=True,
    )

    print()
    print("TEST RESULT:", result)


if __name__ == "__main__":
    main()
