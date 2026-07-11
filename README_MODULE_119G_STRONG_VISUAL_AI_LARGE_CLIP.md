
# Module 119G Strong Visual AI Large CLIP

119F không khác nhiều vì nó không nhìn lại clip. 119G đổi thật:
- model mặc định: `openai/clip-vit-large-patch14`
- mạnh hơn `openai/clip-vit-base-patch32`
- vote theo nhiều frame trong mỗi clip
- giảm lỗi decor ôm quá nhiều người/CDCR/stage
- vẫn bỏ Proxy/Proxies

Lần đầu chạy sẽ tải model lớn, chậm hơn.

## Test 80 file

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

python scripts/create_strong_visual_ai_recognizer_119g.py --project "$PROJECT" --source "$SRC" --frame-samples 7 --max-files 80

(Get-Content "$PROJECT\stt_visual_ai_scene_tags_v1.json" -Raw | ConvertFrom-Json).scene_counts

python scripts/create_scene_review_contact_sheets_121.py --project "$PROJECT" --max-per-tag 80
```

## Full

```powershell
python scripts/create_strong_visual_ai_recognizer_119g.py --project "$PROJECT" --source "$SRC" --frame-samples 7 --max-files 0

python scripts/create_strict_semantic_story_planner_120d.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`
