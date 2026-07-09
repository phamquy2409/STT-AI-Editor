from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.manual_live import run_live_manual_review_existing_project


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STT AI Live Manual Review Server")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--input-json", default=None)
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    run_live_manual_review_existing_project(
        project_root=Path(args.project),
        input_json=Path(args.input_json) if args.input_json else None,
        port=args.port,
    )


if __name__ == "__main__":
    main()
