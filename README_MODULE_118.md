# Module 118 - Real Audio Beat / Energy Analyzer

Cần `ffmpeg` trong PATH để phân tích beat thật từ mp3/m4a. Nếu chưa có ffmpeg, module vẫn fallback BPM grid.

```powershell
python scripts/test_real_audio_beat_energy_analyzer.py
python scripts/create_real_audio_beat_energy_analyzer.py --project "D:\STT Projects\Wedding_Test_001" --target-seconds 180
```
