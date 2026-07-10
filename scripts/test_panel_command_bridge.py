from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.panel_command_bridge import create_panel_command_bridge

def main() -> None:
    print("Module import OK: Panel Command Bridge")
    print("Function:", create_panel_command_bridge)

if __name__ == "__main__":
    main()
