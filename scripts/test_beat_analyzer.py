from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.beat_analyzer.analyzer import create_beat_analyzer

def main() -> None:
    print("Module import OK: 114 Beat Analyzer")
    print("Function:", create_beat_analyzer)

if __name__ == "__main__":
    main()
