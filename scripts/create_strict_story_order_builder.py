
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.strict_story_order_builder.builder import create_strict_story_order_builder

def main() -> None:
    p = argparse.ArgumentParser(description="Build strict story-order wedding timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--target-seconds", type=float, default=180.0)
    p.add_argument("--target-shots", type=int, default=76)
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_strict_story_order_builder(
        project_root=a.project,
        source_folder=a.source,
        target_seconds=a.target_seconds,
        target_shots=a.target_shots,
        timebase=a.timebase,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
