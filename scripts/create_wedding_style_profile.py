
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.style_profile import create_wedding_style_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update STT Wedding Style Profile.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    result = create_wedding_style_profile(project_root=args.project, notes=args.notes)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
