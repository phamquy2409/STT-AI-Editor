# STT AI Editor - Module 119B: Full Length Beat Locked Timeline

Fix lỗi 119 chỉ ra ~112s dù target 180s.

119B:
- phân bố toàn bộ 48 clip trên đủ 180 giây
- chọn boundary gần cut point/beat thật từ 118
- không lấy 48 cut đầu rồi dừng sớm

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_beat_locked_timeline_builder.py
python scripts/create_beat_locked_timeline_builder.py --project "D:\STT Projects\Wedding_Test_001" --target-seconds 180
python scripts/export_final_music_sync_xml_polish.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --preset vertical_1080_25p
```
