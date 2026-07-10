# Module 101D - XML Source Folder Fallback

Fix trường hợp 101B báo JSON lỗi `NO_REAL_SOURCE_PATH_FOUND`.

Nguyên nhân: timeline cũ chỉ có item giả `prewedding_clip_1`, không có path file gốc. 101D sẽ fallback lấy file thật trực tiếp từ source folder để XML không bị offline.

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_premiere_xml_real_source_path_fix.py
```

## Tạo XML mới

```powershell
python scripts/repair_prewedding_xml_real_source_paths.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --preset vertical_1080_25p
```

Nếu muốn lấy nhiều clip hơn:

```powershell
python scripts/repair_prewedding_xml_real_source_paths.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --fallback-clip-count 40
```
