from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.music_sync_timeline_builder.builder import create_music_sync_timeline_builder

def main() -> None:
    print("Module import OK: 115 Music Sync Timeline Builder")
    print("Function:", create_music_sync_timeline_builder)

if __name__ == "__main__":
    main()
