
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremiereBridgeExporter, PremiereXMLValidator


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Premiere XML before import.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--xml", default=None)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    xml_path = Path(args.xml) if args.xml else PremiereBridgeExporter(args.project).find_latest_xml()

    if not xml_path:
        raise SystemExit("Không tìm thấy XML. Hãy export XML trước.")

    validator = PremiereXMLValidator(xml_path)
    result = validator.validate()
    reports = validator.write_reports(xml_path.parent)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("Reports:")
    print(json.dumps(reports, ensure_ascii=False, indent=2))

    if not args.no_open:
        try:
            os.startfile(xml_path.parent)
            html_report = reports.get("html")
            if html_report:
                os.startfile(html_report)
        except Exception:
            pass

    if result.get("errors"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
