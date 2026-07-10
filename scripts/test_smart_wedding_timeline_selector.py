
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.smart_wedding_timeline_selector.selector import create_smart_wedding_timeline_selector

def main() -> None:
    print("Module import OK: 111B Smart Wedding Selector Min Count Fix")
    print("Function:", create_smart_wedding_timeline_selector)

if __name__ == "__main__":
    main()
