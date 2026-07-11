# 100B Premiere Safe Video Only XML

Fix lỗi clip bị sọc trong Premiere và lỗi nhạc.

Bản này:
- xuất XML video-only, không nhúng nhạc
- đo duration bằng ffprobe/cv2 nếu có
- clamp source_in/source_out để không vượt media
- nếu không đo được duration thì dùng slice ngắn an toàn
- output file riêng: `stt_learned_profile_premiere_import_SAFE_VIDEO_ONLY.xml`

## Chạy

```powershell
python scripts/export_premiere_safe_video_only_xml_100b.py --project "D:\STT Projects\Wedding_Test_001" --style-profile "intimate_7_8min" --preset horizontal_4k --fps 30
```

Import file này:

```text
D:\STT Projects\Wedding_Test_001\stt_learned_profile_premiere_import_SAFE_VIDEO_ONLY.xml
```

Đừng import file cũ `stt_learned_profile_premiere_import.xml` nữa.
