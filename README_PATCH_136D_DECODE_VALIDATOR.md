# Patch 136D — Decode Validator

136C only checked numeric duration. Some camera files still show striped missing media
inside Premiere even when `source_overflow_count = 0`.

136D validates the exact source window by decoding sample frames.

It will:

- inspect only the sources used by the final timeline
- compare JSON duration with OpenCV frame duration
- use the shorter duration
- keep 1 second away from file edges by default
- sample 6 frames across every selected window
- shift the source window inward when possible
- replace a source when no safe window can be decoded
- use an unused source with the same tag/family
- rebuild video-only XML directly through 128D
- rebuild the stereo 48 kHz WAV

## Install

Extract over:

```text
D:\Projects\STT-AI-Editor
```

## Run

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/fix_decode_source_and_export_136d.py --project "$PROJECT" --source-safety-sec 1.0 --music-root "D:\27thang6pschh"
```

## Expected

```text
unresolved_count       : 0
source_overflow_count  : 0
gap_count              : 0
overlap_count          : 0
build_128d -> ok       : true
music_ok               : true
```

## Import

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Then use STT Audio Bridge and select:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```
