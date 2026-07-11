
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.multi_style_profile_learner.learner import create_multi_style_profile_learner

def main() -> None:
    p = argparse.ArgumentParser(description="Learn multiple editing style profiles from a dataset folder.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--dataset", default="D:/STT Learning Dataset")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_multi_style_profile_learner(
        project_root=a.project,
        dataset_root=a.dataset,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
