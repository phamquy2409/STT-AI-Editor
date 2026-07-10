
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.prewedding_xml.exporter import export_prewedding_xml, to_pathurl, PRESETS

def main() -> None:
    print("Module import OK: 101E Premiere Safe FCP7 XML")
    print("Function:", export_prewedding_xml)
    print("Presets:", sorted(PRESETS.keys()))
    print("Pathurl test:", to_pathurl(Path("D:/5thang5test/test file.MP4")))

if __name__ == "__main__":
    main()
