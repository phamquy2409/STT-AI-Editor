from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.learned_style_pipeline.pipeline import create_learned_profile_xml_exporter
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--output-xml", default="")
    p.add_argument("--no-open", action="store_true")
    a=p.parse_args()
    res=create_learned_profile_xml_exporter(a.project, a.style_profile, a.preset, a.fps, a.output_xml or None, not a.no_open)
    print(json.dumps(res, ensure_ascii=False, indent=2))
if __name__=="__main__": main()
