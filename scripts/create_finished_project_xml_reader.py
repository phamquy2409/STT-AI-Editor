
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finished_project_xml_reader.reader import create_finished_project_xml_reader

def main() -> None:
    p = argparse.ArgumentParser(description="Read finished Premiere/FCP XML with robust recovery scanner.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--final-xml", default="D:/STT Projects/Wedding_Test_001/final_by_user.xml")
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--include-audio", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_finished_project_xml_reader(
        project_root=a.project,
        source_folder=a.source,
        final_xml=a.final_xml,
        timebase=a.timebase,
        video_only=not a.include_audio,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
