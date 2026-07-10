from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.bad_shot_killer_v2 import create_bad_shot_killer_v2

def main() -> None:
    print("Module import OK: Bad Shot Killer V2")
    print("Function:", create_bad_shot_killer_v2)

if __name__ == "__main__":
    main()
