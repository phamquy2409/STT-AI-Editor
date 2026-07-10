
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.wedding_source_analyzer_v2.analyzer import create_wedding_source_analyzer_v2

def main() -> None:
    p = argparse.ArgumentParser(description="Analyze wedding documentary source files.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/5thang5test")
    p.add_argument("--max-files", type=int, default=252)
    p.add_argument("--full", action="store_true", help="Use 3 sample frames per clip instead of quick 2-frame mode.")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_wedding_source_analyzer_v2(
        project_root=a.project,
        source_folder=a.source,
        max_files=a.max_files,
        quick=not a.full,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
