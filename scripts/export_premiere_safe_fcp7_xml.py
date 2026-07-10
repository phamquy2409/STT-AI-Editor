
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.prewedding_xml.exporter import export_prewedding_xml

def main() -> None:
    p = argparse.ArgumentParser(description="Export Premiere safe FCP7 XML with real source paths.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default=None)
    p.add_argument("--intent", default="prewedding_reel_60s")
    p.add_argument("--preset", default="vertical_1080_25p")
    p.add_argument("--fallback-clip-count", type=int, default=20)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    res = export_prewedding_xml(
        project_root=a.project,
        source_folder=a.source,
        intent=a.intent,
        preset=a.preset,
        fallback_clip_count=a.fallback_clip_count,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
