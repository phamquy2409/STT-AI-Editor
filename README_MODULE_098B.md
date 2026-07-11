# 098B Safe Learned In-Out Picker

Fix vấn đề 098 lấy source_in trung bình quá sâu, ví dụ:

`avg_learned_source_start_sec: 644.623`

098B:
- nếu filename trùng clip đã học: dùng source_in đã học của filename đó
- nếu filename chưa học: dùng source_in an toàn 0.3–3 giây
- ghi đè lại `stt_learned_inout_timeline_v1.json` để 099/100 dùng tiếp

## Chạy

```powershell
python scripts/create_safe_learned_inout_picker_098b.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min"

python scripts/create_profile_music_sync_bridge.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min" --music-folder "D:\STT Music"

python scripts/export_learned_profile_xml.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min" --preset horizontal_4k --fps 30
```
