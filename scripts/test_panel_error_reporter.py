from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.panel_error_reporter import create_panel_error_reporter

def main() -> None:
    print("Module import OK: Panel Error Reporter")
    print("Function:", create_panel_error_reporter)

if __name__ == "__main__":
    main()
