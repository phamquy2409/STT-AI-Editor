
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremiereBridgeExporter, PremiereScriptInstaller


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    installer = PremiereScriptInstaller(project_root)
    latest = PremiereBridgeExporter(project_root).find_latest_xml()

    print("Module 040 Premiere Script Installer import OK.")
    print("Project:", project_root)
    print("AppData:", installer.appdata_dir)
    print("Pointer:", installer.latest_xml_pointer)

    folders = installer.find_premiere_script_folders()
    print("Detected Premiere Script folders:")
    if folders:
        for folder in folders:
            print("-", folder)
    else:
        print("- None detected yet. Safe Documents folder will still be created.")

    if latest:
        print("Latest XML:", latest)
        print()
        print("Create/install script:")
        print("python scripts/install_premiere_script.py")
    else:
        print("WARNING: Không tìm thấy XML.")
        print("Hãy Export Latest Manual XML trước.")


if __name__ == "__main__":
    main()
