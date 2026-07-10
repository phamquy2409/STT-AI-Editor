from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.auto_music_picker.picker import create_auto_music_picker

def main() -> None:
    print("Module import OK: 113 Auto Music Picker")
    print("Function:", create_auto_music_picker)

if __name__ == "__main__":
    main()
