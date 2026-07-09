from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremiereBridgeExporter


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    exporter = PremiereBridgeExporter(project_root=project_root)

    print("Module 037 Premiere Bridge import OK.")
    print("Project:", project_root)

    latest = exporter.find_latest_xml()
    if latest:
        print("Latest XML:", latest)
        print()
        print("Create bridge package:")
        print("python scripts/export_premiere_bridge.py")
    else:
        print("WARNING: Không tìm thấy XML.")
        print("Hãy mở GUI > Export Latest Manual XML trước, rồi chạy:")
        print("python scripts/export_premiere_bridge.py")


if __name__ == "__main__":
    main()
