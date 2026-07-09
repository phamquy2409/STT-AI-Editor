
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_xml import PREWEDDING_XML_PRESETS, export_prewedding_xml


def main() -> None:
    parser = argparse.ArgumentParser(description="Export prewedding selection to Premiere XML.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--selection", default=None)
    parser.add_argument("--preset", default=None, choices=[None] + sorted(PREWEDDING_XML_PRESETS))
    parser.add_argument("--sequence-name", default=None)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = export_prewedding_xml(
        project_root=args.project,
        selection_path=args.selection,
        preset=args.preset,
        sequence_name=args.sequence_name,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
