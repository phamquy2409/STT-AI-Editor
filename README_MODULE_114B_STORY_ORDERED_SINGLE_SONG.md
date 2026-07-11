
# 114B Story Ordered Single Song

Dùng khi chỉ có 1 bài nhạc 3-4 phút.

Fix:
- không ép intimate_7_8min khi chỉ có 1 bài
- timeline tự lấy độ dài theo nhạc, cap tối đa 240s
- giữ thứ tự source/chapter, không chọn cảnh lộn xộn theo điểm đẹp
- vẫn snap cut vào beat grid 112
- ghi đè `stt_beat_snapped_beauty_timeline_v1.json` để dùng lại exporter 115

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

python scripts/create_story_ordered_single_song_timeline_114b.py --project "$PROJECT" --source "$SRC" --style-profile "$PROFILE" --target-seconds 0 --target-shots 220 --min-beauty 42 --allow-review

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`
