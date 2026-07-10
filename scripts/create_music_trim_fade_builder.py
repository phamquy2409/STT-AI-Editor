from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.music_trim_fade_builder.builder import create_music_trim_fade_builder

def main() -> None:
    p = argparse.ArgumentParser(description="Music Trim + Fade Builder")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--intent", default="wedding_documentary")
    p.add_argument("--target-seconds", type=float, default=180.0)
    p.add_argument("--music-in", type=float, default=None)
    p.add_argument("--fade-in", type=float, default=2.0)
    p.add_argument("--fade-out", type=float, default=3.0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    res = create_music_trim_fade_builder(project_root=a.project, intent=a.intent, target_seconds=a.target_seconds, music_in=a.music_in, fade_in=a.fade_in, fade_out=a.fade_out, open_folder=not a.no_open)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
