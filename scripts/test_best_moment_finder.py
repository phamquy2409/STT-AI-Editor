from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.moment import find_best_moments_existing_project
from core.review import generate_preview_review_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    result = find_best_moments_existing_project(
        project_root=project_root,
        roughcut_json=None,
        refined_segment_seconds=2.2,
        sample_step_seconds=0.25,
    )

    review = generate_preview_review_existing_project(
        project_root=project_root,
        roughcut_json=Path(result["refined_json"]),
    )

    print()
    print("BEST MOMENT FILES:")
    for name, path in result.items():
        print(f"{name}: {path}")

    print()
    print("REVIEW FILES:")
    for name, path in review.items():
        print(f"{name}: {path}")

    html_path = review.get("html")
    if html_path and Path(html_path).exists():
        print()
        print("Opening review.html ...")
        os.startfile(html_path)


if __name__ == "__main__":
    main()
