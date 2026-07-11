
# Module 119B Original Source Only

Fix lỗi 119 quét nhầm file proxy:
- bỏ qua folder `Proxy`, `Proxies`
- bỏ qua file `_Proxy.mov`, `-Proxy.mov`, ` proxy.mov`
- ghi đè lại `stt_visual_ai_scene_tags_v1.json` để 120 dùng source gốc

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

python scripts/create_visual_ai_scene_recognizer_119b_original_only.py --project "$PROJECT" --source "$SRC" --frame-samples 8 --max-files 0

python scripts/create_visual_ai_story_beat_planner_120.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`

Kiểm tra không còn proxy:
```powershell
Select-String -Path "$PROJECT\stt_visual_ai_scene_tags_v1.json" -Pattern "Proxy|Proxies|_Proxy"
```
Nếu không hiện dòng nào là đúng.
