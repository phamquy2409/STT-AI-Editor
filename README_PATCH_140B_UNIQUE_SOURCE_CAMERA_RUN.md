# Patch 140B — Unique Source + Camera Run

140 produced:

```text
duplicate_source_count : 11
max_camera_run_final   : 8
```

Do not use that XML as the accepted build.

140B:

1. finds every repeated source path;
2. keeps the most important occurrence;
3. replaces the other occurrences with unused sources;
4. prioritizes same event, then same section/tag/family;
5. never uses proxies or known bad files;
6. improves long camera runs only after source uniqueness is clean;
7. runs 136E hard-fit and rebuilds XML/WAV;
8. validates the final timeline again after 136E.

The bundled 136E is also patched so duplicate rows inside the camera map cannot
reintroduce the same source.

## Install

Extract over:

```text
D:\Projects\STT-AI-Editor
```

## Run

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/run_unique_source_camera_run_140b.py --project "$PROJECT" --max-camera-run 6 --max-camera-changes 10 --music-root "D:\27thang6pschh"
```

Use max camera run 6 first. The source selection quality is more important than
forcing every camera run down to 4.

## Required result

```text
duplicate_source_final    : 0
dedupe_unresolved_count   : 0
gap_count                 : 0
overlap_count             : 0
hard_fit_build -> ok      : true
```

A max camera run around 6–8 can still be accepted when there is no safe alternate
angle from the same event.

## Import

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Then use STT Audio Bridge and select:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```
