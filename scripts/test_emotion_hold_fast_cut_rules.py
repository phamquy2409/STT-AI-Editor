from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.emotion_hold_fast_cut_rules.rules import create_emotion_hold_fast_cut_rules

def main() -> None:
    print("Module import OK: 123 Emotion Hold / Fast Cut Rules")
    print("Function:", create_emotion_hold_fast_cut_rules)

if __name__ == "__main__":
    main()
