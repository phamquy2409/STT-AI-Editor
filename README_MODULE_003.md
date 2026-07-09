# STT AI Editor - Module 003: Shot Detector

Copy files into `D:\Projects\STT-AI-Editor`.

Run:

```powershell
python scripts/test_shot_detector.py
```

Or:

```powershell
python main.py detect-shots --project "D:\STT Projects\Wedding_Test_001" --segment-seconds 3
```

This reads all scanned videos from:

`D:\STT Projects\Wedding_Test_001\database\stt_ai.db`

Then creates timeline segments in the `shot_segments` table.

This is not final AI selection yet. It prepares analyzable segments for the next module: Vision AI.
