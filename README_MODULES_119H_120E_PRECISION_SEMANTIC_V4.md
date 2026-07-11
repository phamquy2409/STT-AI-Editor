# Modules 119H + 120E Precision Semantic V4

Fix theo feedback:
- decor không được lẫn CDCR / khách / sân khấu / game
- detail_beauty thêm detail chú rể: cufflinks, tie, suit, watch, shoes, perfume
- ending ưu tiên 2 người / CDCR, không lấy CR bước lên sân khấu
- vow tối / game / cuối chương trình bị demote
- stage context rõ hơn

## Chạy test

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

python scripts/create_precision_semantic_recognizer_119h.py --project "$PROJECT" --source "$SRC" --frame-samples 7 --max-files 80

python scripts/create_scene_review_contact_sheets_121.py --project "$PROJECT" --max-per-tag 80
```

## Chạy full + export

```powershell
python scripts/create_precision_semantic_recognizer_119h.py --project "$PROJECT" --source "$SRC" --frame-samples 7 --max-files 0

python scripts/create_precision_story_planner_120e.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`
