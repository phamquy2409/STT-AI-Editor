from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.auto_music_picker.picker import create_auto_music_picker

def main() -> None:
    p = argparse.ArgumentParser(description="Auto Music Picker")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--intent", default="wedding_documentary")
    p.add_argument("--target-seconds", type=float, default=180.0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    res = create_auto_music_picker(project_root=a.project, intent=a.intent, target_seconds=a.target_seconds, open_folder=not a.no_open)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
