# Module 128H3 — No Video Delete Fix

128H2 had a critical bug:

- the panel used QE `addTracks()`
- then removed a video track
- Premiere could remove the real V1 instead of the temporary track
- result: all video disappeared and only music remained

128H3:

- never calls `addTracks()`
- never removes a video track
- uses the existing A1 from the video-only sequence
- verifies video clip count before and after inserting music

## Install

Extract over:

```text
D:\Projects\STT-AI-Editor
```

Run:

```powershell
cd D:\Projects\STT-AI-Editor
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_128h_extension.ps1
```

Close Premiere completely and reopen it.

## Important

The sequence that already lost video should not be reused.

Import again:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Open the newly imported sequence, then:

```text
Window > Extensions (Legacy) > STT Audio Bridge
```

Click:

```text
Import + dat nhac Stereo
```

Choose:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```

Music will be inserted into A1 without changing V1.
