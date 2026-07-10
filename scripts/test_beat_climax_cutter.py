from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.beat_climax_cutter import create_beat_climax_cutter

def main() -> None:
    print("Module import OK: Beat / Climax Cutter")
    print("Function:", create_beat_climax_cutter)

if __name__ == "__main__":
    main()
