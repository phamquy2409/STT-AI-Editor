# Modules 123 + 123B Taste AI Learner

## 123 học từ timeline anh đã dựng thật

Nó học:
- file nào anh dùng
- file nào dùng nhiều lần
- camera/prefix nào anh thường dùng
- tag nào anh dùng ở intro/story/build/climax/ending
- độ dài shot theo từng phần
- source in trung bình
- giữ slow minimum 50%

Yêu cầu đã có:
`D:\STT Projects\Wedding_Test_001\stt_finished_project_xml_v1.json`

Nếu chưa có, chạy lại module 091D trước.

## Chạy 123

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/create_taste_ai_learner_123.py --project "$PROJECT" --profile-name "single_song_report_3_4min"
```

Output:
`D:\STT Projects\Wedding_Test_001\stt_taste_profile_v1.json`

## Chạy planner 123B

```powershell
python scripts/create_taste_boosted_planner_123b.py --project "$PROJECT" --style-profile "single_song_report_3_4min" --target-seconds 210 --target-shots 180

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "single_song_report_3_4min" --preset horizontal_4k --fps 30
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`

## Khi có thêm XML sau này

Mỗi project đưa vào dataset riêng rồi chạy learner lại. Profile sẽ ngày càng ổn hơn.
