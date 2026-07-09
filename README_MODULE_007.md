# STT AI Editor - Module 007: Premiere XML Exporter

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_premiere_exporter.py
```

Or:

```powershell
python main.py premiere-xml --project "D:\STT Projects\Wedding_Test_001" --fps 25 --width 3840 --height 2160
```

Output is saved in the latest roughcut folder:

`stt_ai_premiere_import.xml`

Import in Premiere:

1. Open Premiere Pro.
2. File > Import.
3. Select `stt_ai_premiere_import.xml`.

This Build 007 exporter includes video + stereo audio tracks.
