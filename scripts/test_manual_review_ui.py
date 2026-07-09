
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.manual_review import generate_manual_review_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    result = generate_manual_review_existing_project(project_root=project_root, input_json=None)

    print()
    print("MODERN MANUAL REVIEW FILES:")
    for key, value in result.items():
        print(f"{key}: {value}")

    html = Path(result["html"])
    if html.exists():
        os.startfile(html)


if __name__ == "__main__":
    main()
