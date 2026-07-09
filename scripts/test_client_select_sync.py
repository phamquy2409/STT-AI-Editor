from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.client_select_sync import create_client_select_sync_plan

def main() -> None:
    print("Module import OK: Client Select Sync")
    print("Function:", create_client_select_sync_plan)

if __name__ == "__main__":
    main()
