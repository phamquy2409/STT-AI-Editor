from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.sfx_placeholder import create_sfx_placeholder_manager

def main() -> None:
    print("Module import OK: SFX Placeholder Manager")
    print("Function:", create_sfx_placeholder_manager)
    print("Run script in scripts folder.")

if __name__ == "__main__":
    main()
