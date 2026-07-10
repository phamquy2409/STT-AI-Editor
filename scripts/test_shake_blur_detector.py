from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.shake_blur_detector import create_shake_blur_detector

def main() -> None:
    print("Module import OK: Shake / Blur Detector")
    print("Function:", create_shake_blur_detector)

if __name__ == "__main__":
    main()
