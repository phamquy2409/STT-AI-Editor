# Module 101E - Premiere Safe FCP7 XML

Fix lỗi 101D tạo XML có source thật nhưng Premiere báo `File Import Failure`.

101E tạo XML theo cấu trúc FCP7 an toàn hơn:
- tên file gốc thật
- pathurl encode sạch
- file metadata đầy đủ hơn
- video + dual mono A1/A2
- validate XML trước khi ghi pointer

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_premiere_safe_fcp7_xml.py
```

## Tạo XML mới

```powershell
python scripts/export_premiere_safe_fcp7_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --preset vertical_1080_25p --fallback-clip-count 20
```

Nếu 20 clip import OK thì thử 40:

```powershell
python scripts/export_premiere_safe_fcp7_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --preset vertical_1080_25p --fallback-clip-count 40
```

Import lại:
`D:\STT Projects\Wedding_Test_001\stt_prewedding_premiere_import.xml`

Nếu panel vẫn lỗi, thử Premiere `File > Import` thủ công.
