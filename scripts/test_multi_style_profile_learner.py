
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.multi_style_profile_learner.learner import create_multi_style_profile_learner, discover_dataset

def main() -> None:
    print("Module import OK: 093B Multi Style Profile Dataset Learner")
    print("Function:", create_multi_style_profile_learner)
    print("Discover function:", discover_dataset)

if __name__ == "__main__":
    main()
