from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.review_package import create_review_package
def main() -> None:
    print("Module import OK: Review Package")
    print("Function:", create_review_package)
if __name__=="__main__": main()
