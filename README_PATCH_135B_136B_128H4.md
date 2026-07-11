# Patch 135B–136B + 128H4

Fixes the first 134–136 run:

- 147 intervals from 106 source shots
- 41 reused sources
- 74 section mismatches
- same camera run of 11
- Unicode console crash while printing Korean music filename

## Run

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/run_safe_135b_136b_128h4.py --project "$PROJECT" --target-seconds 210 --music-root "D:\27thang6pschh"
```

Expected:

```text
interval_count equals source_shot_count
reused_source_count = 0
section_mismatch_count near 0
gap_count = 0
overlap_count = 0
source_overflow_count = 0
```

Import:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Then use the already-installed STT Audio Bridge panel and choose:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```
