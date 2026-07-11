# Modules 108-111 Quality Gate + Music V2

Sửa các lỗi hiện tại:
- còn vài đoạn sọc/lỗi source
- chọn scene rung, lia máy lung tung, không ý nghĩa
- đoạn cần dài lại cắt nhanh / đoạn cần nhanh lại dài

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="intimate_7_8min"

python scripts/create_source_quality_analyzer_108.py --project "$PROJECT" --source "$SRC" --sample-count 7 --max-files 0

python scripts/create_quality_filtered_source_timeline_109.py --project "$PROJECT" --min-score 55 --keep-review --reject-shaky --reject-blur --reject-empty

python scripts/create_music_directed_quality_timeline_110.py --project "$PROJECT" --style-profile "$PROFILE" --target-seconds 480 --target-shots 220

python scripts/export_quality_music_xml_111.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:

```text
D:\STT Projects\Wedding_Test_001\stt_quality_music_v2_premiere_import.xml
```

Nếu còn sọc, gửi output dòng:
- unknown_duration_count
- gap_count
- duration_stats
- motion_counts
