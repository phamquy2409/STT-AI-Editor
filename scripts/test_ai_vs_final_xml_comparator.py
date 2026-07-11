
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_vs_final_xml_comparator.comparator import create_ai_vs_final_xml_comparator

def main() -> None:
    print("Module import OK: 092 AI vs Final XML Comparator")
    print("Function:", create_ai_vs_final_xml_comparator)

if __name__ == "__main__":
    main()
