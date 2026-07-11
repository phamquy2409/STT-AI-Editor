# Modules 105-107 Music Director

Đổi hướng từ "beat peak detection" sang "music director map".

105:
- đọc nhạc
- chia bài thành các block cảm xúc:
  quiet_hold / emotion_long / story_medium / build_fast / climax_fast / impact_cut / ending_hold
- tạo file manual để chỉnh tay nếu auto chưa đúng:
  `D:\STT Projects\Wedding_Test_001\stt_music_director_manual.csv`

106:
- dựng timeline theo từng block nhạc
- không cắt đều
- không random source
- source đi theo order/chapter

107:
- export XML video-only gapless
- giữ duration dài/ngắn

## Chạy với Enemy Of Truth

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$PROFILE="intimate_7_8min"

$MUSIC=(Get-ChildItem "D:\27thang6pschh" -Recurse -File |
Where-Object { $_.Name -like "*Enemy Of Truth*" -or $_.Name -like "*진실의 적*" } |
Select-Object -First 1).FullName

$MUSIC

python scripts/create_music_director_map_105.py --project "$PROJECT" --music "$MUSIC" --target-seconds 480

python scripts/create_music_directed_timeline_106.py --project "$PROJECT" --style-profile "$PROFILE" --target-seconds 480 --target-shots 220

python scripts/export_music_directed_xml_107.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30 --preserve-unknown-duration
```

Import:

```text
D:\STT Projects\Wedding_Test_001\stt_music_directed_premiere_import.xml
```

Kéo đúng bài nhạc vào timeline tại 00:00:00:00.
