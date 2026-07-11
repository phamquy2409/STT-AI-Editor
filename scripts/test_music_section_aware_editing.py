from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.music_section_aware_editing.editor import create_music_section_aware_editing

def main() -> None:
    print("Module import OK: 122 Music Section Aware Editing")
    print("Function:", create_music_section_aware_editing)

if __name__ == "__main__":
    main()
