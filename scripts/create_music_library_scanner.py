from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.music_library_scanner.scanner import create_music_library_scanner

def main() -> None:
    p = argparse.ArgumentParser(description="Music Library Scanner")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--music", default="D:/STT Music")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    res = create_music_library_scanner(project_root=a.project, music_folder=a.music, open_folder=not a.no_open)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
