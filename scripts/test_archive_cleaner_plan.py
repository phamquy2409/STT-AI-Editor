from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.archive_cleaner_plan import create_archive_cleaner_plan

def main() -> None:
    print("Module import OK: Archive Cleaner Plan")
    print("Function:", create_archive_cleaner_plan)

if __name__ == "__main__":
    main()
