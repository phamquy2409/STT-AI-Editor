from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.smart_inout_cutter import create_smart_inout_cutter

def main() -> None:
    print("Module import OK: Smart In-Out Cutter")
    print("Function:", create_smart_inout_cutter)

if __name__ == "__main__":
    main()
