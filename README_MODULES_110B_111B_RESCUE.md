# Modules 110B-111B Rescue Non-zero XML

Dùng khi 111 xuất `timeline_count: 0`.

Nguyên nhân thường gặp:
- 109/110 lọc source quá gắt
- path trong timeline không còn tồn tại
- 111 skip hết clip nên Premiere mở lên không có source

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"
$PROFILE="intimate_7_8min"

python scripts/create_quality_music_rescue_timeline_110b.py --project "$PROJECT" --source "$SRC" --style-profile "$PROFILE" --target-seconds 480 --target-shots 220 --min-score 30

python scripts/export_quality_music_rescue_xml_111b.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import:

```text
D:\STT Projects\Wedding_Test_001\stt_quality_music_rescue_premiere_import.xml
```

Nếu `timeline_count` vẫn 0, chạy bản nới hết:

```powershell
python scripts/create_quality_music_rescue_timeline_110b.py --project "$PROJECT" --source "$SRC" --style-profile "$PROFILE" --target-seconds 480 --target-shots 220 --min-score 0 --allow-braw

python scripts/export_quality_music_rescue_xml_111b.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30 --preserve-unknown-duration
```
