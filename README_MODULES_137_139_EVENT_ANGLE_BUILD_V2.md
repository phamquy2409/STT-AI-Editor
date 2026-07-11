# Modules 137–139 — Event, Angle, Wedding Build V2

## 137 — Event Context Mapper V2

Earlier event grouping used creation time and found zero multi-camera events.

137 instead uses:

- camera-local source order
- final timeline positions
- music section
- semantic family
- interpolation between the STT and STTA timeline anchors

It creates:

```text
stt_event_context_map_v2.json
```

## 138 — Event-Aware Angle Director

138 keeps the story slot unchanged but may replace a source with another source from
the same event.

It prefers:

- same scene tag or semantic family
- another camera when the camera run is too long
- better quality and beauty score
- different shot scale
- no source reuse
- no known bad files

It creates:

```text
stt_event_aware_timeline_v2.json
```

## 139 — Wedding Director Build V2

139 runs:

```text
137 Event Context
138 Event-Aware Angle
136E Hard Fit + Decode Safety
128D Video-Only XML
Stereo WAV build
```

## Install

Extract over:

```text
D:\Projects\STT-AI-Editor
```

## Run everything

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/run_wedding_director_build_v2_139.py --project "$PROJECT" --music-root "D:\27thang6pschh" --max-camera-run 4 --max-replacements 24
```

137 and 138 do not decode all source files.
136E only validates sources selected for the final timeline.

## Results

```text
D:\STT Projects\Wedding_Test_001\stt_event_context_map_v2.json
D:\STT Projects\Wedding_Test_001\stt_event_aware_timeline_v2.json
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```

Import the video-only XML, then use the installed STT Audio Bridge panel and choose
the stereo WAV.

## Important values

137:

```text
event_count
multi_camera_event_count
```

138:

```text
replacement_count
max_camera_run_before
max_camera_run_after
```

136E:

```text
unresolved_count = 0
hard_fit_failure_count = 0
source_overflow_count = 0
gap_count = 0
overlap_count = 0
```
