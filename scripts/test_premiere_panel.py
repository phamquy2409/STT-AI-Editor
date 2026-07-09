
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremiereBridgeExporter, PremierePanelInstaller


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    installer = PremierePanelInstaller(project_root)
    latest = PremiereBridgeExporter(project_root).find_latest_xml()

    print("Module 041 Premiere Panel Starter import OK.")
    print("Project:", project_root)
    print("AppData pointer:", installer.latest_xml_pointer)
    print("User CEP extensions:", installer.get_user_cep_extensions_dir())

    if latest:
        print("Latest XML:", latest)
        print()
        print("Create/install panel starter:")
        print("python scripts/create_premiere_panel.py")
    else:
        print("WARNING: Không tìm thấy XML.")
        print("Hãy Export Latest Manual XML trước.")


if __name__ == "__main__":
    main()
