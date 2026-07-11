# Modules 119-120 Visual AI Scene Recognition

Đây là bản đúng ý "AI phải tự nhận diện", không đổi tên file thủ công.

119:
- dùng CLIP local để đọc frame trong từng video
- tự tag: intro_beauty / cdcr / makeup / ceremony_giatien / guest_food / party...
- không dựa vào filename

120:
- dựng timeline theo scene AI nhận diện + cut map + beat grid
- không đưa guest_food vào đoạn CDCR/intro

## Cài dependency một lần

```powershell
python -m pip install -U torch torchvision transformers pillow opencv-python
```

Lần đầu chạy 119 sẽ tải model `openai/clip-vit-base-patch32`.

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="single_song_report_3_4min"

python scripts/create_visual_ai_scene_recognizer_119.py --project "$PROJECT" --source "$SRC" --frame-samples 8 --max-files 0

python scripts/create_visual_ai_story_beat_planner_120.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`

Nếu muốn test nhanh:
```powershell
python scripts/create_visual_ai_scene_recognizer_119.py --project "$PROJECT" --source "$SRC" --frame-samples 5 --max-files 80
```
