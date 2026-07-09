# STT AI Editor - Module 004: Vision Analyzer

Copy files into:

`D:\Projects\STT-AI-Editor`

Run first test:

```powershell
python scripts/test_vision_analyzer.py
```

This analyzes only the first 80 pending segments.

If OK, run all remaining segments:

```powershell
python main.py analyze-vision --project "D:\STT Projects\Wedding_Test_001"
```

Or analyze only 200 segments:

```powershell
python main.py analyze-vision --project "D:\STT Projects\Wedding_Test_001" --limit 200
```

Scores saved into SQLite table `shot_segments`:

- blur_score = sharpness score, higher is better
- exposure_score = exposure quality, higher is better
- motion_score = movement amount
- shake_score = stability score, higher is more stable
- beauty_score = technical beauty
- ai_keep_score = rough keep candidate score

This is the first real Vision AI preparation module.
