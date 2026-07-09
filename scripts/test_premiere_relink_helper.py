from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.premiere_relink_helper import create_premiere_relink_report
def main() -> None:
    print("Module import OK: Premiere Relink Helper")
    print("Function:", create_premiere_relink_report)
if __name__=="__main__": main()
