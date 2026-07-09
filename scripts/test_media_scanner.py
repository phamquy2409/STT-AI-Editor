from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.media import scan_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    # Sua duong dan source video that cua anh o dong nay neu can.
    # Vi du:
    # source_folder = Path("D:/Wedding/Source")
    source_folder = None

    result = scan_existing_project(project_root, source_folder=source_folder)

    print()
    print("TEST RESULT:", result)


if __name__ == "__main__":
    main()
