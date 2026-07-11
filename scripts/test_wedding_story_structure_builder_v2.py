
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.wedding_story_structure_builder_v2.story import create_wedding_story_structure_builder_v2

def main() -> None:
    print("Module import OK: 126 Wedding Story Structure Builder V2")
    print("Function:", create_wedding_story_structure_builder_v2)

if __name__ == "__main__":
    main()
