
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_style_memory import build_ai_style_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build STT AI Style Memory V2.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--intent", default="wedding_highlight")
    parser.add_argument("--notes", default=None)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = build_ai_style_memory(
        project_root=args.project,
        intent=args.intent,
        notes=args.notes,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
