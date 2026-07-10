from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.panel_source_folder import create_panel_source_folder_config

def main() -> None:
    print("Module import OK: Panel Source Folder Config")
    print("Function:", create_panel_source_folder_config)

if __name__ == "__main__":
    main()
