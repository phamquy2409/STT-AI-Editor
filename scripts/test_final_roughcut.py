from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.exporter import export_premiere_xml_existing_project
from core.final_cut import build_final_roughcut_existing_project
from core.review import generate_preview_review_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    final_cut = build_final_roughcut_existing_project(
        project_root=project_root,
        input_json=None,
        target_duration_seconds=60.0,
        min_final_score=20.0,
        max_segments_per_video=2,
    )

    xml = export_premiere_xml_existing_project(
        project_root=project_root,
        roughcut_json=Path(final_cut["final_json"]),
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    )

    review = generate_preview_review_existing_project(
        project_root=project_root,
        roughcut_json=Path(final_cut["final_json"]),
    )

    print()
    print("FINAL ROUGH CUT FILES:")
    for name, path in final_cut.items():
        print(f"{name}: {path}")

    print()
    print("PREMIERE XML FILES:")
    for name, path in xml.items():
        print(f"{name}: {path}")

    print()
    print("REVIEW FILES:")
    for name, path in review.items():
        print(f"{name}: {path}")

    html_path = review.get("html")
    if html_path and Path(html_path).exists():
        print()
        print("Opening final review.html ...")
        os.startfile(html_path)


if __name__ == "__main__":
    main()
