# Modules 124–125 Quality Gate + Smart Moment Picker

## 124 – Shot Quality Gate V3

Phân tích nhiều đoạn trong từng source:
- rung/lắc
- whip/pan mạnh
- out nét
- quá tối/quá sáng
- độ tương phản
- cửa sổ ổn định đẹp nhất

## 125 – Smart In/Out Moment Picker

Giữ nguyên story và cách chọn source của 123B, nhưng:
- đổi source in/out sang đoạn ổn định hơn
- tránh đầu/cuối clip
- tránh đoạn rung, blur, quá tối
- có thể thay source yếu bằng source khác cùng tag/cùng phần story
- không thay đổi độ dài timeline hay beat

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"

python scripts/create_shot_quality_gate_v3_124.py --project "$PROJECT" --source "$SRC" --windows 10 --sample-span 1.1 --frames-per-window 5 --analyze-all

python scripts/create_smart_inout_moment_picker_125.py --project "$PROJECT" --min-quality 46 --replace-weak

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "single_song_report_3_4min" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`

## Chạy nhanh chỉ các source đang nằm trên timeline

Bỏ `--analyze-all`:

```powershell
python scripts/create_shot_quality_gate_v3_124.py --project "$PROJECT" --source "$SRC" --windows 10 --sample-span 1.1 --frames-per-window 5
```

Nhưng muốn 125 thay source rung bằng source khác thì nên dùng `--analyze-all`.
