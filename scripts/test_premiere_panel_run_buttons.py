from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.premiere_panel_run_buttons import create_premiere_panel_run_buttons

def main() -> None:
    print("Module import OK: Premiere Panel Run Buttons")
    print("Function:", create_premiere_panel_run_buttons)

if __name__ == "__main__":
    main()
