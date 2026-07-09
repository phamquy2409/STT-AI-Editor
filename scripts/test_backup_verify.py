from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.backup_verify import create_backup_verify_report

def main() -> None:
    print("Module import OK: Backup Verify Report")
    print("Function:", create_backup_verify_report)

if __name__ == "__main__":
    main()
