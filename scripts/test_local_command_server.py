from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.local_command_server import create_local_command_server_report, start_local_command_server_background

def main() -> None:
    print("Module import OK: Local Command Server")
    print("Function:", create_local_command_server_report)
    print("Background function:", start_local_command_server_background)

if __name__ == "__main__":
    main()
