# STT AI Editor - Module 121: Beat Sync V2 / More Cut Points

121 sửa cảm giác "cắt xong chèn nhạc" bằng cách:
- tăng shot count mặc định lên 76 shot / 180s
- intro + climax cắt nhanh hơn
- story/gia tiên/vow giữ vừa phải
- snap cut boundary gần real peak/cut point từ 118
- dùng lại report source 110 để chọn nhiều source sạch hơn

## Cài
Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_beat_sync_v2_more_cut_points.py
python scripts/create_beat_sync_v2_more_cut_points.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --target-seconds 180 --target-shots 76
python scripts/export_final_music_sync_xml_polish.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --preset vertical_1080_25p
```

Nếu clip quá nhanh, giảm `--target-shots 64`.
Nếu còn chậm, tăng `--target-shots 85`.
