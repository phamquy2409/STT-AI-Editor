from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.wedding_scene import classify_wedding_scenes_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    result = classify_wedding_scenes_existing_project(
        project_root=project_root,
        input_json=None,
    )

    print()
    print("WEDDING SCENE FILES:")
    for name, path in result.items():
        print(f"{name}: {path}")

    output_dir = Path(result["output_dir"])
    if output_dir.exists():
        print()
        print("Opening output folder ...")
        os.startfile(output_dir)


if __name__ == "__main__":
    main()
