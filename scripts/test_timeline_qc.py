from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.timeline_qc import create_timeline_qc_report

def main() -> None:
    print("Module import OK: Timeline QC Report")
    print("Function:", create_timeline_qc_report)
    print("Run script in scripts folder.")

if __name__ == "__main__":
    main()
