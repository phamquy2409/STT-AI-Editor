from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.delivery_handoff import create_delivery_handoff_package

def main() -> None:
    print("Module import OK: Delivery Handoff Package")
    print("Function:", create_delivery_handoff_package)
    print("Run script in scripts folder.")

if __name__ == "__main__":
    main()
