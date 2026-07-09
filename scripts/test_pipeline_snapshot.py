from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.pipeline_snapshot import create_pipeline_snapshot
def main() -> None:
    print("Module import OK: Pipeline Snapshot")
    print("Function:", create_pipeline_snapshot)
if __name__=="__main__": main()
