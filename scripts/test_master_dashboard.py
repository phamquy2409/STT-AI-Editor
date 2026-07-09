from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.master_dashboard import create_master_dashboard
def main() -> None:
    print("Module import OK: Master Dashboard")
    print("Function:", create_master_dashboard)
if __name__=="__main__": main()
