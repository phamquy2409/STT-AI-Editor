from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pipeline import run_one_click_pipeline_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    # Existing test project already has scan/detect/analyze done.
    # This starts from candidate expansion to avoid wasting time.
    result = run_one_click_pipeline_existing_project(
        project_root=project_root,
        source_folder=Path("D:/5thang5test"),
        run_from_scratch=False,
        target_duration_seconds=60.0,
        top_candidates=120,
    )

    print()
    print("ONE CLICK PIPELINE RESULT:")
    print(f"status: {result.get('status')}")
    print(f"run_dir: {result.get('run_dir')}")
    print(f"final_json: {result.get('final_json')}")
    print(f"premiere_xml: {result.get('premiere_xml')}")
    print(f"review_html: {result.get('review_html')}")
    print(f"manual_review_html: {result.get('manual_review_html')}")

    manual_html = result.get("manual_review_html")
    review_html = result.get("review_html")

    if manual_html and Path(manual_html).exists():
        print()
        print("Opening manual_review.html ...")
        os.startfile(manual_html)
    elif review_html and Path(review_html).exists():
        print()
        print("Opening review.html ...")
        os.startfile(review_html)


if __name__ == "__main__":
    main()
