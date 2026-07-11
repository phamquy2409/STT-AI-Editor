# 098C Force Safe Source In

Fix clip bị sọc/lỗi source trong Premiere do source in/out bị sâu hoặc vượt media.

098C:
- bỏ toàn bộ source_in học quá sâu
- ép source_in chỉ khoảng 0.1–0.8s
- ghi đè `stt_learned_inout_timeline_v1.json`
- sau đó chạy lại 099 và 100 để xuất XML mới

## Chạy

```powershell
python scripts/create_force_safe_source_in_098c.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min"

python scripts/create_profile_music_sync_bridge.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min" --music-folder "D:\27thang6pschh"

python scripts/export_learned_profile_xml.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min" --preset horizontal_4k --fps 30
```
