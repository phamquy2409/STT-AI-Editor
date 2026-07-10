
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.smart_wedding_timeline_selector.selector import create_smart_wedding_timeline_selector

def main() -> None:
    p = argparse.ArgumentParser(description="Create clean wedding timeline using analyzer report from module 110.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/5thang5test")
    p.add_argument("--intent", default="wedding_documentary", choices=[
        "wedding_documentary",
        "wedding_highlight_3min",
        "wedding_teaser_60s",
        "gia_tien_story",
        "reception_story",
    ])
    p.add_argument("--target-seconds", type=float, default=180.0)
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--min-order-gap", type=int, default=0)
    p.add_argument("--no-review", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_smart_wedding_timeline_selector(
        project_root=a.project,
        source_folder=a.source,
        intent=a.intent,
        target_seconds=a.target_seconds,
        timebase=a.timebase,
        min_order_gap=a.min_order_gap,
        allow_review=not a.no_review,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
