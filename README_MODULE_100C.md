# 100C Gapless Premiere Safe XML

Fix lỗi 100B:
- giữa 2 source bị hở đoạn
- clip bị sọc do clipitem duration nhỏ hơn source out
- timeline được tính bằng frame nối sát nhau, không còn khoảng hở

## Chạy

```powershell
python scripts/export_gapless_premiere_safe_xml_100c.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min" --preset horizontal_4k --fps 30 --force-source-zero
```

Import file mới này:

```text
D:\STT Projects\Wedding_Test_001\stt_learned_profile_premiere_import_GAPLESS_SAFE.xml
```

Nếu vẫn có clip lỗi, gửi output có `unknown_duration_count`.
