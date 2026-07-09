from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.delivery_checklist import create_delivery_checklist

def main() -> None:
    print("Module import OK: Delivery Checklist")
    print("Function:", create_delivery_checklist)

if __name__ == "__main__":
    main()
