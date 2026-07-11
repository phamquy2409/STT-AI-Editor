# Modules 116B-118B Story Beat Scene Map

Fix:
- chỗ cần CDCR không được nhét cảnh khách ăn uống
- intro beauty phải là detail/venue/dress/ring
- cắt nhanh/chậm theo block nhạc rõ hơn
- cần map scene tag để AI hiểu cảnh

## Chạy lần đầu

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

python scripts/create_music_cut_map_116b.py --project "$PROJECT" --target-seconds 0 --overwrite

python scripts/create_scene_tags_117b.py --project "$PROJECT" --source "$SRC"

python scripts/create_story_beat_locked_planner_118b.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`

## Quan trọng

Sau khi chạy 117B, mở file:
`D:\STT Projects\Wedding_Test_001\stt_scene_tags_manual.csv`

Sửa cột `scene_tag` cho các file bị đoán sai:
- `intro_beauty`
- `cdcr`
- `makeup`
- `ceremony_giatien`
- `ruoc_dau`
- `reception_stage`
- `guest_food`
- `party`
- `family`
- `ending`
- `other`

Nếu file khách ăn uống bị nhét vào CDCR, đổi `scene_tag` thành `guest_food`.
Nếu file CDCR bị tag sai, đổi thành `cdcr`.
Sau đó chạy lại 117B + 118B + 115, không cần chạy lại 116B.
