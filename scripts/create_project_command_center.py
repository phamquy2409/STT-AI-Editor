
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.project_command_center import create_project_command_center


def main() -> None:
    parser = argparse.ArgumentParser(description="Create STT project command center.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = create_project_command_center(
        project_root=args.project,
        repo_root=args.repo,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
