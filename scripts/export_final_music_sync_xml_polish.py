from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.final_music_sync_xml_polish.exporter import export_final_music_sync_xml_polish

def main() -> None:
    p = argparse.ArgumentParser(description="Final Music Sync XML Polish")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/5thang5test")
    p.add_argument("--intent", default="wedding_documentary")
    p.add_argument("--preset", default="vertical_1080_25p")
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    res = export_final_music_sync_xml_polish(project_root=a.project, source_folder=a.source, intent=a.intent, preset=a.preset, timebase=a.timebase, open_folder=not a.no_open)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
