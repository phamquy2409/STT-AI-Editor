from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.background_app_start_helper import create_background_app_start_helper

def main() -> None:
    print("Module import OK: Background App Start Helper")
    print("Function:", create_background_app_start_helper)

if __name__ == "__main__":
    main()
