from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.final_wedding_music_cut_xml.exporter import export_final_wedding_music_cut_xml

def main() -> None:
    print("Module import OK: 125 Final Wedding Music Cut XML")
    print("Function:", export_final_wedding_music_cut_xml)

if __name__ == "__main__":
    main()
