from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.audio_ducking_fade_plan.plan import create_audio_ducking_fade_plan

def main() -> None:
    print("Module import OK: 124 Audio Ducking + Fade Plan")
    print("Function:", create_audio_ducking_fade_plan)

if __name__ == "__main__":
    main()
