from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.local_command_server import start_local_command_server

def main() -> None:
    parser = argparse.ArgumentParser(description="Start STT Local Command Server.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    start_local_command_server(project_root=args.project, port=args.port, block=True)

if __name__ == "__main__":
    main()
