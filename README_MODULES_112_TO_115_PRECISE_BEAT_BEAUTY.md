# Modules 112-115 Precise Beat + Scene Beauty

Mục tiêu:
- cut đúng beat hơn
- chọn scene đẹp hơn
- tìm đoạn đẹp/stable bên trong từng source, không chỉ chọn file

## Chạy với Enemy Of Truth

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="intimate_7_8min"

$MUSIC=(Get-ChildItem "D:\27thang6pschh" -Recurse -File |
Where-Object { $_.Name -like "*Enemy Of Truth*" -or $_.Name -like "*진실의 적*" } |
Select-Object -First 1).FullName

$MUSIC

python scripts/create_precise_beat_grid_112.py --project "$PROJECT" --music "$MUSIC" --target-seconds 480

python scripts/create_scene_beauty_analyzer_113.py --project "$PROJECT" --source "$SRC" --sample-windows 6 --max-files 0

python scripts/create_beat_snapped_beauty_timeline_114.py --project "$PROJECT" --source "$SRC" --style-profile "$PROFILE" --target-seconds 480 --target-shots 220 --min-beauty 50

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:

```text
D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml
```

Nếu 113 lâu, test nhanh trước:

```powershell
python scripts/create_scene_beauty_analyzer_113.py --project "$PROJECT" --source "$SRC" --sample-windows 4 --max-files 120
```
