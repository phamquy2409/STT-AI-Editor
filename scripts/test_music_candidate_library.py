from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.music_library import create_music_candidate_library

def main() -> None:
    print("Module import OK: Music Candidate Library")
    print("Function:", create_music_candidate_library)
    print("Run script in scripts folder.")

if __name__ == "__main__":
    main()
