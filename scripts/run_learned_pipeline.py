from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.exporter import export_premiere_xml_existing_project
from core.feedback_learning import apply_feedback_existing_project, learn_feedback_existing_project
from core.manual_review import generate_manual_review_existing_project
from core.review import generate_preview_review_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    learn = learn_feedback_existing_project(project_root=project_root)

    learned = apply_feedback_existing_project(
        project_root=project_root,
        target_duration_seconds=60.0,
        max_segments_per_video=1,
    )

    xml = export_premiere_xml_existing_project(
        project_root=project_root,
        roughcut_json=Path(learned["learned_json"]),
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    )

    review = generate_preview_review_existing_project(
        project_root=project_root,
        roughcut_json=Path(learned["learned_json"]),
    )

    manual = generate_manual_review_existing_project(
        project_root=project_root,
        input_json=Path(learned["learned_json"]),
    )

    result = {
        "learn": learn,
        "learned": learned,
        "xml": xml,
        "review": review,
        "manual": manual,
    }

    print()
    print("LEARNED PIPELINE RESULT:")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    html = Path(manual["html"])
    if html.exists():
        os.startfile(html)

    xml_path = Path(xml["xml"])
    if xml_path.exists():
        print()
        print(f"XML folder: {xml_path.parent}")


if __name__ == "__main__":
    main()
