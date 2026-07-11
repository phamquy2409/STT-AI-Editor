
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_vs_final_xml_comparator.comparator import create_ai_vs_final_xml_comparator

def main() -> None:
    p = argparse.ArgumentParser(description="Compare AI XML against user's finished XML.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--ai-xml", default="D:/STT Projects/Wedding_Test_001/stt_final_wedding_music_cut_premiere_import.xml")
    p.add_argument("--final-xml", default="D:/STT Projects/Wedding_Test_001/final_by_user.xml")
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_ai_vs_final_xml_comparator(
        project_root=a.project,
        source_folder=a.source,
        ai_xml=a.ai_xml,
        final_xml=a.final_xml,
        timebase=a.timebase,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
