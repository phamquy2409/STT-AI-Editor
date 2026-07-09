from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.sfx_placeholder import create_sfx_placeholder_manager

def main() -> None:
    parser = argparse.ArgumentParser(description="SFX Placeholder Manager.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    result = create_sfx_placeholder_manager(project_root=args.project, open_folder=not args.no_open)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
