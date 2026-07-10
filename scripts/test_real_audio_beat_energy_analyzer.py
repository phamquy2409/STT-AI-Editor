from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.real_audio_beat_energy_analyzer.analyzer import create_real_audio_beat_energy_analyzer

def main() -> None:
    print("Module import OK: 118 Real Audio Beat / Energy Analyzer")
    print("Function:", create_real_audio_beat_energy_analyzer)

if __name__ == "__main__":
    main()
