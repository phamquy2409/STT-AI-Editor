
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.beat_locked_timeline_builder.builder import create_beat_locked_timeline_builder

def main() -> None:
    print("Module import OK: 119B Full Length Beat Locked Timeline")
    print("Function:", create_beat_locked_timeline_builder)

if __name__ == "__main__":
    main()
