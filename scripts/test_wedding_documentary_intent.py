
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.wedding_documentary_intent.router import create_wedding_documentary_intent_timeline

def main() -> None:
    print("Module import OK: 109 Wedding Documentary Intent Router")
    print("Function:", create_wedding_documentary_intent_timeline)

if __name__ == "__main__":
    main()
