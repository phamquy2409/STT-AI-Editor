from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.duplicate_remover import remove_duplicate_shots_existing_project
from core.exporter import export_premiere_xml_existing_project
from core.manual_review import generate_manual_review_existing_project
from core.review import generate_preview_review_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    result = remove_duplicate_shots_existing_project(
        project_root=project_root,
        input_json=None,
        fill_pool_json=None,
        target_duration_seconds=60.0,
    )

    xml = export_premiere_xml_existing_project(
        project_root=project_root,
        roughcut_json=Path(result["no_duplicates_json"]),
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    )

    review = generate_preview_review_existing_project(
        project_root=project_root,
        roughcut_json=Path(result["no_duplicates_json"]),
    )

    manual = generate_manual_review_existing_project(
        project_root=project_root,
        input_json=Path(result["no_duplicates_json"]),
    )

    print()
    print("DUPLICATE REMOVER FILES:")
    for name, path in result.items():
        print(f"{name}: {path}")

    print()
    print("PREMIERE XML FILES:")
    for name, path in xml.items():
        print(f"{name}: {path}")

    print()
    print("REVIEW FILES:")
    for name, path in review.items():
        print(f"{name}: {path}")

    print()
    print("MANUAL REVIEW FILES:")
    for name, path in manual.items():
        print(f"{name}: {path}")

    html = Path(manual["html"])
    if html.exists():
        print()
        print("Opening manual_review.html ...")
        os.startfile(html)


if __name__ == "__main__":
    main()
