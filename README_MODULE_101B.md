# Module 101B - Premiere XML Real Source Path Fix v2

Fix lỗi XML dùng source giả `prewedding_clip_1`.

## Cài
Giải nén, copy trực tiếp `core`, `scripts`, `README_MODULE_101B.md` vào:
`D:\Projects\STT-AI-Editor`

## Test
```powershell
python scripts/test_premiere_xml_real_source_path_fix.py
```

## Tạo lại XML source thật
```powershell
python scripts/repair_prewedding_xml_real_source_paths.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --preset vertical_1080_25p
```

Import lại:
`D:\STT Projects\Wedding_Test_001\stt_prewedding_premiere_import.xml`
