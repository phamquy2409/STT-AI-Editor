from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.master_dashboard import create_master_dashboard
def main() -> None:
    parser=argparse.ArgumentParser(description="Master Dashboard.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--no-open", action="store_true")
    args=parser.parse_args()
    result=create_master_dashboard(project_root=args.project, open_folder=not args.no_open)
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__=="__main__": main()
