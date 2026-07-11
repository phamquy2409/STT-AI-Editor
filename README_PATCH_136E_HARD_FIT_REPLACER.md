# Patch 136E — Hard Fit Replacer

136D found and replaced one bad source, but one timeline slot still did not fit
inside the usable source duration after keeping a 1-second safety margin.

136E requires:

```text
usable source duration >= timeline shot duration
```

When the current source is too short, it replaces it with an unused source that:

- is long enough for the timeline slot
- has the same scene tag or semantic family
- preferably belongs to the same music section
- passes direct frame decoding
- still keeps one second away from both source edges

## Install

Extract over:

```text
D:\Projects\STT-AI-Editor
```

## Run

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/fix_hard_fit_source_and_export_136e.py --project "$PROJECT" --source-safety-sec 1.0 --music-root "D:\27thang6pschh"
```

## Expected

```text
unresolved_count        : 0
hard_fit_failure_count  : 0
source_overflow_count   : 0
gap_count               : 0
overlap_count           : 0
build_128d -> ok        : true
music_ok                : true
```

## Import

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Then use STT Audio Bridge and select:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```
