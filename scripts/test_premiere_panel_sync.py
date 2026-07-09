
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremierePanelSync


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    sync = PremierePanelSync(project_root)

    print("Module 043 Premiere Panel Sync import OK.")
    print("Project:", project_root)
    print("Status JSON:", sync.status_json)
    print("Status TXT:", sync.status_txt)

    latest = sync.pointer.find_latest_xml()
    if latest:
        print("Latest XML:", latest)
        print()
        print("Run sync:")
        print("python scripts/sync_premiere_panel.py")
    else:
        print("WARNING: Không tìm thấy XML. Export Latest Manual XML trước.")


if __name__ == "__main__":
    main()
