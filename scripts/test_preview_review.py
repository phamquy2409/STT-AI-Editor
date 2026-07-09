from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.review import generate_preview_review_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    paths = generate_preview_review_existing_project(
        project_root=project_root,
        roughcut_json=None,
    )

    print()
    print("PREVIEW REVIEW FILES:")
    for name, path in paths.items():
        print(f"{name}: {path}")

    html_path = paths.get("html")
    if html_path and Path(html_path).exists():
        print()
        print("Opening review.html ...")
        os.startfile(html_path)


if __name__ == "__main__":
    main()
