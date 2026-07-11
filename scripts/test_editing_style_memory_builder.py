
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.editing_style_memory_builder.builder import create_editing_style_memory_builder

def main() -> None:
    print("Module import OK: 093 Editing Style Memory Builder")
    print("Function:", create_editing_style_memory_builder)

if __name__ == "__main__":
    main()
