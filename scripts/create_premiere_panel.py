
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import create_premiere_panel


def main() -> None:
    parser = argparse.ArgumentParser(description="Create STT AI Editor Premiere CEP panel starter.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--xml", default=None)
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = create_premiere_panel(
        project_root=args.project,
        xml_path=args.xml,
        install_to_user_cep=not args.no_install,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
