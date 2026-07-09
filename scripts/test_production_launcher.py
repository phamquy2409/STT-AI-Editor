from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.production_launcher import create_production_launcher

def main() -> None:
    print("Module import OK: Production Launcher")
    print("Function:", create_production_launcher)
    print("Run script in scripts folder.")

if __name__ == "__main__":
    main()
