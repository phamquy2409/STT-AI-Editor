from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.beat_sync_v2.sync import create_beat_sync_v2_more_cut_points

def main() -> None:
    print('Module import OK: 121 Beat Sync V2 More Cut Points')
    print('Function:', create_beat_sync_v2_more_cut_points)
if __name__=='__main__': main()
