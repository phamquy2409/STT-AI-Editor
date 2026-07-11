
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.wedding_story_role_classifier.classifier import create_wedding_story_role_classifier

def main() -> None:
    p = argparse.ArgumentParser(description="Classify wedding source into strict story chapters.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--order-mode", default="chapter_then_time", choices=["chapter_then_time", "time_then_chapter"])
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_wedding_story_role_classifier(
        project_root=a.project,
        source_folder=a.source,
        order_mode=a.order_mode,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
