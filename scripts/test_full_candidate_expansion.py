from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.expansion import expand_candidates_existing_project
from core.exporter import export_premiere_xml_existing_project
from core.final_cut import build_final_roughcut_existing_project
from core.moment import find_best_moments_existing_project
from core.people_composition import analyze_people_composition_existing_project
from core.review import generate_preview_review_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    expanded = expand_candidates_existing_project(
        project_root=project_root,
        top_candidates=120,
        min_ai_score=30.0,
        max_segments_per_video=6,
    )

    best = find_best_moments_existing_project(
        project_root=project_root,
        roughcut_json=Path(expanded["roughcut_plan_json"]),
        refined_segment_seconds=2.2,
        sample_step_seconds=0.33,
    )

    people = analyze_people_composition_existing_project(
        project_root=project_root,
        input_json=Path(best["refined_json"]),
    )

    final_cut = build_final_roughcut_existing_project(
        project_root=project_root,
        input_json=Path(people["people_json"]),
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
    print("FULL SOURCE EXPANSION FILES:")
    for name, path in expanded.items():
        print(f"{name}: {path}")

    print()
    print("BEST MOMENT FILES:")
    for name, path in best.items():
        print(f"{name}: {path}")

    print()
    print("PEOPLE / COMPOSITION FILES:")
    for name, path in people.items():
        print(f"{name}: {path}")

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
