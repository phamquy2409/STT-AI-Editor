
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremiereXMLPointer


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    pointer = PremiereXMLPointer(project_root)

    latest = pointer.find_latest_xml()

    print("Module 042 Premiere pointer import OK.")
    print("Project:", project_root)
    print("Pointer TXT:", pointer.pointer_txt)
    print("Pointer JSON:", pointer.pointer_json)

    if latest:
        print("Latest XML:", latest)
        result = pointer.update(latest, source="test_premiere_pointer")
        print("Updated:", result["pointer_txt"])
    else:
        print("WARNING: Không tìm thấy XML. Export Latest Manual XML trước.")


if __name__ == "__main__":
    main()
