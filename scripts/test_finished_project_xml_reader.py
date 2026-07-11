
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.finished_project_xml_reader.reader import create_finished_project_xml_reader, decode_pathurl, build_file_id_map_from_xml

def main() -> None:
    print("Module import OK: 091D Recovery Scan All Clipitems")
    print("Function:", create_finished_project_xml_reader)
    print("Path decode:", decode_pathurl("file://localhost/D:/STT/source/C0001.MP4"))
    sample = '<file id="file-1"><name>C0001.MP4</name><pathurl>file://localhost/D:/A/C0001.MP4</pathurl></file>'
    print("File map:", build_file_id_map_from_xml(sample))

if __name__ == "__main__":
    main()
