from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.music_library_scanner.scanner import create_music_library_scanner

def main() -> None:
    print("Module import OK: 112 Music Library Scanner")
    print("Function:", create_music_library_scanner)

if __name__ == "__main__":
    main()
