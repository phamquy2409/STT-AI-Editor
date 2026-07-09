from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.client_feedback import create_client_feedback_collector

def main() -> None:
    print("Module import OK: Client Feedback Collector")
    print("Function:", create_client_feedback_collector)

if __name__ == "__main__":
    main()
