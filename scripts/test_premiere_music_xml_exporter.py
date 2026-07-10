
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_music_xml_exporter.exporter import export_premiere_music_sync_xml

def main() -> None:
    print("Module import OK: 116B Premiere Music XML Timecode Fix")
    print("Function:", export_premiere_music_sync_xml)

if __name__ == "__main__":
    main()
