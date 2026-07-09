
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_doctor import check_prewedding_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Check prewedding pipeline installation and project readiness.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = check_prewedding_pipeline(
        project_root=args.project,
        repo_root=args.repo,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
