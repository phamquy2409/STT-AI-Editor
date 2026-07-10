from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.music_trim_fade_builder.builder import create_music_trim_fade_builder

def main() -> None:
    print("Module import OK: 117 Music Trim + Fade Builder")
    print("Function:", create_music_trim_fade_builder)

if __name__ == "__main__":
    main()
