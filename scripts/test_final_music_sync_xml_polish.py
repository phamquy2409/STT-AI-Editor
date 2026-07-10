from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.final_music_sync_xml_polish.exporter import export_final_music_sync_xml_polish

def main() -> None:
    print("Module import OK: 120 Final Music Sync XML Polish")
    print("Function:", export_final_music_sync_xml_polish)

if __name__ == "__main__":
    main()
