from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.exporter import export_premiere_xml_existing_project
from core.review import generate_preview_review_existing_project
from core.story import build_story_timeline_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    story = build_story_timeline_existing_project(
        project_root=project_root,
        input_json=None,
        target_duration_seconds=60.0,
        max_segments_per_video=1,
    )

    xml = export_premiere_xml_existing_project(
        project_root=project_root,
        roughcut_json=Path(story["story_json"]),
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    )

    review = generate_preview_review_existing_project(
        project_root=project_root,
        roughcut_json=Path(story["story_json"]),
    )

    print()
    print("STORY TIMELINE STRONG DIVERSITY FILES:")
    for name, path in story.items():
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
        print("Opening story review.html ...")
        os.startfile(html_path)


if __name__ == "__main__":
    main()
