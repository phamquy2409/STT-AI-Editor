from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.exporter import export_premiere_xml_existing_project
from core.manual_review import generate_manual_review_existing_project
from core.pipeline_v2 import run_wedding_pipeline_v2_existing_project
from core.project_presets import get_project_workflow_values, save_project_workflow_preset
from core.review import generate_preview_review_existing_project


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STT AI Wedding Pipeline V2 with a workflow preset.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--preset", default="wedding_highlight_60s")
    args = parser.parse_args()

    project_root = Path(args.project)
    preset = save_project_workflow_preset(project_root, args.preset)
    values = get_project_workflow_values(project_root, args.preset)

    print("USING PRESET:")
    print(json.dumps(values, ensure_ascii=False, indent=2))

    result = run_wedding_pipeline_v2_existing_project(
        project_root=project_root,
        target_duration_seconds=float(values["target_duration"]),
        max_segments_per_video=int(values["max_segments_per_video"]),
    )

    print()
    print("PIPELINE RESULT:")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    html = result.get("manual_review_html") or result.get("review_html")
    if html and Path(html).exists():
        os.startfile(html)

    xml = result.get("premiere_xml")
    if xml and Path(xml).exists():
        print()
        print("XML folder:")
        print(Path(xml).parent)


if __name__ == "__main__":
    main()
