# Module 140 — Camera Run Breaker V2

140 keeps the source-selection quality of 139 and only targets long same-camera runs.

Important pipeline fix:

```text
138 previously wrote stt_event_aware_timeline_v2.json
136E read stt_final_cut_beat_timeline_v2.json
```

So the 138 angle changes could fail to reach the final XML.

140 now:

1. reads `stt_event_aware_timeline_v2.json` first;
2. breaks long camera runs conservatively;
3. writes the result into:
   - `stt_camera_run_balanced_timeline_v2.json`
   - `stt_final_cut_beat_timeline_v2.json`
   - `stt_multicam_directed_timeline_v1.json`
4. runs 136E hard-fit and decode safety;
5. rebuilds the 128H video-only XML and stereo WAV.

## Rules

- protect hero, climax and ending shots;
- first try an unused angle from the same event;
- same tag or semantic family;
- prefer another camera;
- no source reuse;
- if no unused event angle exists, swap two selected sources inside the same section/family;
- keep timeline position and duration unchanged;
- do not force replacement when there is no safe option.

## Install

Extract over:

```text
D:\Projects\STT-AI-Editor
```

## Run

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/run_camera_run_breaker_v2_140.py --project "$PROJECT" --max-camera-run 5 --max-changes 16 --music-root "D:\27thang6pschh"
```

Use `--max-camera-run 5` first. Do not force 4 immediately because it can damage source quality.

## Expected values

```text
max_camera_run_before          : about 11
max_camera_run_after_balance   : lower than before
duplicate_source_count         : 0
gap_count                      : 0
overlap_count                  : 0
hard_fit_build -> ok           : true
```

## Import

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Then use STT Audio Bridge and select:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```
