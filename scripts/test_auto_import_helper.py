from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.auto_import_helper import create_auto_import_helper

def main() -> None:
    print("Module import OK: Auto Import Helper")
    print("Function:", create_auto_import_helper)

if __name__ == "__main__":
    main()
