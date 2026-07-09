from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.final_production_dashboard import create_final_production_dashboard

def main() -> None:
    print("Module import OK: Final Production Dashboard")
    print("Function:", create_final_production_dashboard)

if __name__ == "__main__":
    main()
