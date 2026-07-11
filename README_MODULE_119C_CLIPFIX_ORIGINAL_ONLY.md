
# Module 119C CLIP Model Fix + Original Only

Fix lỗi:
`'BaseModelOutputWithPooling' object has no attribute 'norm'`

Đồng thời vẫn bỏ qua Proxy/Proxies và file `_Proxy.mov`.

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

Remove-Item "$PROJECT\stt_visual_ai_scene_tags_v1.json" -Force -ErrorAction SilentlyContinue

python scripts/create_visual_ai_scene_recognizer_119c_clipfix_original_only.py --project "$PROJECT" --source "$SRC" --frame-samples 8 --max-files 0

python scripts/create_visual_ai_story_beat_planner_120.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`
