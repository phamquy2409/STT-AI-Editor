# Module 141 — Story Continuity Director

140B improved source uniqueness and camera balance. 141 focuses on how selected
shots connect to each other.

It does not select a new group of 106 shots.

It only performs conservative local source swaps within the same music section.

## Continuity rules

- reduce backward jumps in event progression;
- keep shots from the same event close when appropriate;
- avoid abrupt semantic jumps such as decor directly to party and back;
- prefer readable shot-scale progression;
- protect hook, hero, climax, emotional and ending shots;
- never cross music-section boundaries;
- never reuse a source;
- every source must fit the new timeline slot with a one-second safety margin;
- run 136E after ordering and rebuild XML/WAV.

## Install

Extract over:

```text
D:\Projects\STT-AI-Editor
```

## Run

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/run_story_continuity_director_141.py --project "$PROJECT" --lookahead 5 --max-swaps 12 --minimum-improvement 5 --music-root "D:\27thang6pschh"
```

The conservative default is a maximum of 12 swaps. Do not increase it before
reviewing this version in Premiere.

## Results to inspect

```text
swap_count
continuity_cost_before
continuity_cost_after
backward_jump_before
backward_jump_after
severe_backward_before
severe_backward_after
abrupt_family_before
abrupt_family_after
duplicate_source_count
gap_count
overlap_count
hard_fit_build -> ok
```

Lower continuity cost and fewer backward/family jumps are better.

## Change list

```text
D:\STT Projects\Wedding_Test_001\exports\story_continuity_director_141_<time>\CONTINUITY_SWAPS_141.json
```

## Import

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Then use STT Audio Bridge and select:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```
