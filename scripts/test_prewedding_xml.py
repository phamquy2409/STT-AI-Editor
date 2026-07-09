
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_xml import PREWEDDING_XML_PRESETS, PreweddingXMLExporter


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    exporter = PreweddingXMLExporter(project_root)

    print("Module 049 Prewedding XML Exporter import OK.")
    print("Project:", project_root)
    print("Selection:", exporter.find_selection_file())
    print("Project XML:", exporter.project_xml_path)
    print()
    print("Presets:")
    for key, value in PREWEDDING_XML_PRESETS.items():
        print("-", key, "=>", value["label"])
    print()
    print("Run:")
    print("python scripts/export_prewedding_xml.py")


if __name__ == "__main__":
    main()
