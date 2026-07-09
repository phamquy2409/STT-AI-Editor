from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.project_version_tracker import create_project_version_tracker

def main() -> None:
    print("Module import OK: Project Version Tracker")
    print("Function:", create_project_version_tracker)

if __name__ == "__main__":
    main()
