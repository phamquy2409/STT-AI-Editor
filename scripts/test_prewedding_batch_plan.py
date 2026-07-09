from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.prewedding_batch import create_prewedding_batch_plan
def main() -> None:
    print("Module import OK: Prewedding Batch Plan")
    print("Function:", create_prewedding_batch_plan)
if __name__=="__main__": main()
