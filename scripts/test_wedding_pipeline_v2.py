from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pipeline_v2 import run_wedding_pipeline_v2_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    result = run_wedding_pipeline_v2_existing_project(
        project_root=project_root,
        target_duration_seconds=60.0,
        max_segments_per_video=1,
    )

    print()
    print("WEDDING PIPELINE V2 RESULT:")
    print(f"status: {result.get('status')}")
    print(f"run_dir: {result.get('run_dir')}")
    print(f"scene_json: {result.get('scene_json')}")
    print(f"story_json: {result.get('story_json')}")
    print(f"final_json: {result.get('final_json')}")
    print(f"premiere_xml: {result.get('premiere_xml')}")
    print(f"review_html: {result.get('review_html')}")
    print(f"manual_review_html: {result.get('manual_review_html')}")

    html = result.get("manual_review_html") or result.get("review_html")
    if html and Path(html).exists():
        print()
        print("Opening manual_review.html ...")
        os.startfile(html)

    xml = result.get("premiere_xml")
    if xml and Path(xml).exists():
        print()
        print("XML folder:")
        print(Path(xml).parent)


if __name__ == "__main__":
    main()
