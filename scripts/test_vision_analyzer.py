from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.vision import analyze_vision_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    # Test first 80 pending segments to make sure everything works.
    # Later you can run all by command line.
    result = analyze_vision_existing_project(
        project_root=project_root,
        limit=80,
        only_pending=True,
    )

    print()
    print("TEST RESULT:", result)


if __name__ == "__main__":
    main()
