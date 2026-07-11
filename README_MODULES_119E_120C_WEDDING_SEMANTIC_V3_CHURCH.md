# Modules 119E + 120C Wedding Semantic V3 + Church

Tag mới:
- decor
- detail_beauty
- getting_ready
- first_look
- cdcr_portrait
- ceremony_giatien
- church_ceremony
- vow
- ruoc_dau
- reception_stage
- wedding_game
- family_photo
- family_emotion
- guest_food
- party
- ending
- other

## Test 80 file

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

python scripts/create_wedding_semantic_recognizer_119e.py --project "$PROJECT" --source "$SRC" --frame-samples 5 --max-files 80

(Get-Content "$PROJECT\stt_visual_ai_scene_tags_v1.json" -Raw | ConvertFrom-Json).scene_counts
```

## Full + xuất XML

```powershell
python scripts/create_wedding_semantic_recognizer_119e.py --project "$PROJECT" --source "$SRC" --frame-samples 5 --max-files 0

python scripts/create_wedding_semantic_story_planner_120c.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`
