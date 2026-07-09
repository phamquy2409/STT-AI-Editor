
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import update_premiere_xml_pointer


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Premiere latest XML pointer.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--xml", default=None)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = update_premiere_xml_pointer(
        project_root=args.project,
        xml_path=args.xml,
        source="script_update_premiere_xml_pointer",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.no_open:
        try:
            os.startfile(str(Path(result["pointer_txt"]).parent))
        except Exception:
            pass


if __name__ == "__main__":
    main()
