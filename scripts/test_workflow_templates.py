from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.workflow_templates import create_workflow_templates
def main() -> None:
    print("Module import OK: Workflow Templates")
    print("Function:", create_workflow_templates)
if __name__=="__main__": main()
