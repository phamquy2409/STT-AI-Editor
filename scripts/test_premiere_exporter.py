from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.exporter import export_premiere_xml_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    paths = export_premiere_xml_existing_project(
        project_root=project_root,
        roughcut_json=None,
        sequence_fps=25,
        sequence_width=3840,
        sequence_height=2160,
    )

    print()
    print("PREMIERE EXPORT FILES:")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
