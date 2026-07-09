
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremiereBridgeExporter, PremiereJSXHelper


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    latest = PremiereBridgeExporter(project_root).find_latest_xml()

    print("Module 039 Premiere JSX Helper import OK.")
    print("Project:", project_root)

    if latest:
        print("Latest XML:", latest)
        helper = PremiereJSXHelper(project_root)
        targets = helper.find_possible_premiere_script_folders()
        print("Possible Premiere script folders:")
        for t in targets:
            print("-", t)
        print()
        print("Create helper package:")
        print("python scripts/create_premiere_jsx_helper.py")
    else:
        print("WARNING: Không tìm thấy XML.")
        print("Hãy Export Latest Manual XML trước.")


if __name__ == "__main__":
    main()
