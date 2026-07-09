from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.roughcut import build_roughcut_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    paths = build_roughcut_existing_project(
        project_root=project_root,
        target_duration_seconds=60,
        min_keep_score=45,
        max_segments_per_video=2,
    )

    print()
    print("ROUGH CUT FILES:")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
