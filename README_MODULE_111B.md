# STT AI Editor - Module 111B: Smart Wedding Selector Min Count Fix

Fix lỗi 111 chọn còn 5 source.

111B:
- không lọc review quá gắt
- vẫn trừ điểm source rung/out-focus/tối nhưng không bỏ hết
- ép đủ khoảng 48 shot cho wedding_documentary 180s
- co duration thay vì bỏ clip khi gần hết timeline
- ghi vào `stt_prewedding_refined_v1.json` để exporter 101E đọc ngay

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_smart_wedding_timeline_selector.py
```

## Chạy

```powershell
python scripts/create_smart_wedding_timeline_selector.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --target-seconds 180
```

Sau đó export XML:

```powershell
python scripts/export_premiere_safe_fcp7_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --preset vertical_1080_25p --fallback-clip-count 40
```
