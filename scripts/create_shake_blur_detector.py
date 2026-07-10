from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.shake_blur_detector import create_shake_blur_detector

def main() -> None:
    p = argparse.ArgumentParser(description="Shake / Blur Detector")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/5thang5test")
    p.add_argument("--intent", default="prewedding_reel_60s")
    p.add_argument("--target-seconds", type=float, default=60.0)
    p.add_argument("--timebase", type=int, default=25)
    p.add_argument("--max-files", type=int, default=120)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    kwargs = {"project_root": a.project, "source_folder": a.source, "intent": a.intent, "target_seconds": a.target_seconds, "timebase": a.timebase, "max_files": a.max_files, "open_folder": not a.no_open}
    result = create_shake_blur_detector(**kwargs)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
