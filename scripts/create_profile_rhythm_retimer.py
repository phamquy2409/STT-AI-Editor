from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.learned_style_pipeline.pipeline import create_profile_rhythm_retimer
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--target-seconds", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a=p.parse_args()
    res=create_profile_rhythm_retimer(a.project, a.style_profile, a.target_seconds or None, not a.no_open)
    print(json.dumps(res, ensure_ascii=False, indent=2))
if __name__=="__main__": main()
