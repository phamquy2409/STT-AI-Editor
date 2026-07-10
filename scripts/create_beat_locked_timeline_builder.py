
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.beat_locked_timeline_builder.builder import create_beat_locked_timeline_builder

def main() -> None:
    p = argparse.ArgumentParser(description="Create full-length beat-locked timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--target-seconds", type=float, default=180.0)
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--min-clip-sec", type=float, default=0.9)
    p.add_argument("--max-clip-sec", type=float, default=6.0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_beat_locked_timeline_builder(
        project_root=a.project,
        target_seconds=a.target_seconds,
        timebase=a.timebase,
        min_clip_sec=a.min_clip_sec,
        max_clip_sec=a.max_clip_sec,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
