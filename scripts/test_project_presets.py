from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.project_presets import (
    get_project_workflow_values,
    list_workflow_presets,
    load_project_workflow_preset,
    save_project_workflow_preset,
)


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    print("AVAILABLE PRESETS:")
    print(json.dumps(list_workflow_presets(), ensure_ascii=False, indent=2))

    print()
    print("SAVE RECOMMENDED PRESET:")
    saved = save_project_workflow_preset(project_root, "wedding_highlight_60s")
    print(json.dumps(saved, ensure_ascii=False, indent=2))

    print()
    print("CURRENT PROJECT PRESET:")
    current = load_project_workflow_preset(project_root)
    print(json.dumps(current, ensure_ascii=False, indent=2))

    print()
    print("GUI VALUES:")
    values = get_project_workflow_values(project_root)
    print(json.dumps(values, ensure_ascii=False, indent=2))

    preset_file = project_root / "stt_workflow_preset.json"
    if preset_file.exists():
        os.startfile(preset_file.parent)


if __name__ == "__main__":
    main()
