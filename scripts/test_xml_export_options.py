from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.xml_options import (
    export_xml_with_options_existing_project,
    list_sequence_presets,
    save_xml_export_settings_existing_project,
)


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    print("SEQUENCE PRESETS:")
    print(json.dumps(list_sequence_presets(), ensure_ascii=False, indent=2))

    print()
    print("SAVE DEFAULT XML EXPORT SETTINGS:")
    settings = save_xml_export_settings_existing_project(
        project_root=project_root,
        sequence_preset="uhd_4k_25p",
    )
    print(json.dumps(settings, ensure_ascii=False, indent=2))

    print()
    print("EXPORT LATEST ROUGHCUT WITH UHD 4K 25P:")
    result = export_xml_with_options_existing_project(
        project_root=project_root,
        roughcut_json=None,
        sequence_preset="uhd_4k_25p",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    xml = Path(result["xml"])
    if xml.exists():
        os.startfile(xml.parent)


if __name__ == "__main__":
    main()
