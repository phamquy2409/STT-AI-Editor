from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from core.music_beat_plan import create_music_beat_plan
def main() -> None:
    print("Module import OK: Music Beat Plan")
    print("Function:", create_music_beat_plan)
if __name__=="__main__": main()
