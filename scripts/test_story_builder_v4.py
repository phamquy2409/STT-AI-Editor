from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.story_builder_v4 import create_story_builder_v4

def main() -> None:
    print("Module import OK: Story Builder V4")
    print("Function:", create_story_builder_v4)

if __name__ == "__main__":
    main()
