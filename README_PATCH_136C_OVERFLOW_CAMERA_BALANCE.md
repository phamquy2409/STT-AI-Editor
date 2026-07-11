# Patch 136C — Overflow + Camera Balance

Fixes:

```text
source_overflow_count : 1
max_same_camera_run   : 14
```

Run:

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/fix_overflow_camera_balance_136c.py --project "$PROJECT" --max-camera-run 4 --music-root "D:\27thang6pschh"
```

Expected:

```text
source_overflow_after : 0
max_same_camera_run_after : lower than before
gap_count : 0
overlap_count : 0
```

Import:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Then use STT Audio Bridge and choose:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```
