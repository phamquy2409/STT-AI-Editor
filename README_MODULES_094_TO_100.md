# STT AI Editor - Modules 094 to 100 Learned Style Pipeline

## Chạy

```powershell
$SRC="D:\27thang6pschh\souce"
$PROJECT="D:\STT Projects\Wedding_Test_001"
$PROFILE="intimate_7_8min"

python scripts/test_learned_style_pipeline_094_100.py

python scripts/create_apply_style_profile.py --project "$PROJECT" --source "$SRC" --style-profile "$PROFILE" --target-seconds 480 --target-shots 180

python scripts/create_learned_source_scorer.py --project "$PROJECT" --source "$SRC" --style-profile "$PROFILE"

python scripts/create_profile_story_timeline_builder.py --project "$PROJECT" --source "$SRC" --style-profile "$PROFILE" --target-seconds 480 --target-shots 180

python scripts/create_profile_rhythm_retimer.py --project "$PROJECT" --style-profile "$PROFILE" --target-seconds 480

python scripts/create_learned_inout_picker.py --project "$PROJECT" --style-profile "$PROFILE"

python scripts/create_profile_music_sync_bridge.py --project "$PROJECT" --style-profile "$PROFILE" --music-folder "D:\STT Music"

python scripts/export_learned_profile_xml.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Output XML:

```text
D:\STT Projects\Wedding_Test_001\stt_learned_profile_premiere_import.xml
```
