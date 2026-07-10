from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.real_source_timeline import create_real_source_timeline

def main() -> None:
    print("Module import OK: Pipeline Real Source Timeline Fix")
    print("Function:", create_real_source_timeline)

if __name__ == "__main__":
    main()
