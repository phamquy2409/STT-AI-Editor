# Module 101C - Fix Prewedding XML Imports

Fix lỗi:

`ImportError: cannot import name 'PREWEDDING_XML_PRESETS'`

sau khi cài 101B.

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_prewedding_xml_imports_fix.py
python scripts/test_premiere_xml_real_source_path_fix.py
```

## Chạy lại XML real source

```powershell
python scripts/repair_prewedding_xml_real_source_paths.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --preset vertical_1080_25p
```
