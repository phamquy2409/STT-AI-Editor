
# Module 122 Wedding AI Export V1

Mục tiêu: không đứng mãi ở nhận diện scene nữa.

Một lệnh sẽ chạy:
1. Visual AI recognizer: 119H / 119G / 119E
2. Story planner: 120E / 120D / 120C
3. Premiere XML exporter: 115
4. Xuất kết quả `stt_beat_snapped_beauty_premiere_import.xml`

## Chạy AI Export V1

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$SRC="D:\27thang6pschh\souce"

python scripts/run_wedding_ai_export_v1_122.py --project "$PROJECT" --source "$SRC" --style-profile "single_song_report_3_4min" --recognizer 119h --planner 120e --frame-samples 7 --target-shots 220 --force-recognize
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`

## Nếu không muốn chạy lại AI nhận diện

Dùng tag hiện có:

```powershell
python scripts/run_wedding_ai_export_v1_122.py --project "$PROJECT" --source "$SRC" --style-profile "single_song_report_3_4min" --recognizer skip --planner 120e --target-shots 220
```

## Nếu muốn vừa export vừa tạo ảnh review

```powershell
python scripts/run_wedding_ai_export_v1_122.py --project "$PROJECT" --source "$SRC" --style-profile "single_song_report_3_4min" --recognizer 119h --planner 120e --frame-samples 7 --target-shots 220 --force-recognize --review
```

## Lưu ý

122 không làm AI thông minh hơn ngay. Nó gom pipeline thành 1 nút export.
Các lỗi nhận diện/taste sẽ xử lý ở module sau:
- 123 Taste AI Learner từ final XML
- 124 Multi-song / intimate 7-8 phút
- 125 Vow / nat sound / speech
