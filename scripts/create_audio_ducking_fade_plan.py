from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.audio_ducking_fade_plan.plan import create_audio_ducking_fade_plan

def main() -> None:
    p = argparse.ArgumentParser(description="Audio Ducking + Fade Plan")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--target-seconds", type=float, default=180.0)
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--music-volume-db", type=float, default=-6.0)
    p.add_argument("--duck-volume-db", type=float, default=-18.0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    res = create_audio_ducking_fade_plan(project_root=a.project, target_seconds=a.target_seconds, timebase=a.timebase, music_volume_db=a.music_volume_db, duck_volume_db=a.duck_volume_db, open_folder=not a.no_open)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
