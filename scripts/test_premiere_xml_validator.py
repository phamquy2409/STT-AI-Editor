
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.premiere_bridge import PremiereBridgeExporter, PremiereXMLValidator


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    exporter = PremiereBridgeExporter(project_root=project_root)

    print("Module 038 Premiere XML Validator import OK.")
    print("Project:", project_root)

    latest = exporter.find_latest_xml()
    if not latest:
        print("WARNING: Không tìm thấy XML.")
        print("Hãy mở GUI > Export Latest Manual XML trước.")
        return

    print("Latest XML:", latest)
    validator = PremiereXMLValidator(latest)
    result = validator.validate()

    print("Status:", result["status"])
    print("Errors:", len(result["errors"]))
    print("Warnings:", len(result["warnings"]))
    print("Video clipitems:", result["counts"].get("video_clipitems"))
    print("Audio clipitems:", result["counts"].get("audio_clipitems"))

    print()
    print("Run full report:")
    print("python scripts/validate_premiere_xml.py")


if __name__ == "__main__":
    main()
