
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.music_placeholder import MUSIC_MOODS, create_music_placeholder_manager


def main() -> None:
    print("Module 062 Music Placeholder Manager import OK.")
    print("Moods:")
    for key in MUSIC_MOODS:
        print("-", key)
    print()
    print("Run:")
    print("python scripts/create_music_placeholder_manager.py --intent prewedding_reel_60s")


if __name__ == "__main__":
    main()
