
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.strict_story_order_builder.builder import create_strict_story_order_builder

def main() -> None:
    print("Module import OK: 126B Strict Story Order Builder")
    print("Function:", create_strict_story_order_builder)

if __name__ == "__main__":
    main()
