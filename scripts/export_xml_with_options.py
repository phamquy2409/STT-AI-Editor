from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.xml_options import export_xml_with_options_existing_project, list_sequence_presets


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Premiere XML with sequence preset.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--roughcut-json", default=None)
    parser.add_argument(
        "--preset",
        default="uhd_4k_25p",
        choices=[p["name"] for p in list_sequence_presets()],
    )
    args = parser.parse_args()

    result = export_xml_with_options_existing_project(
        project_root=Path(args.project),
        roughcut_json=Path(args.roughcut_json) if args.roughcut_json else None,
        sequence_preset=args.preset,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    xml = Path(result["xml"])
    if xml.exists():
        os.startfile(xml.parent)


if __name__ == "__main__":
    main()
