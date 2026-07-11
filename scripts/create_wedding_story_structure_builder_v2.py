
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.wedding_story_structure_builder_v2.story import create_wedding_story_structure_builder_v2

def main() -> None:
    p = argparse.ArgumentParser(description="Build story-structured wedding timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/5thang5test")
    p.add_argument("--target-seconds", type=float, default=180.0)
    p.add_argument("--target-shots", type=int, default=76)
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_wedding_story_structure_builder_v2(
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
