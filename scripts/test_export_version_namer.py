from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.export_version_namer import create_export_version_namer

def main() -> None:
    print("Module import OK: Export Version Namer")
    print("Function:", create_export_version_namer)

if __name__ == "__main__":
    main()
