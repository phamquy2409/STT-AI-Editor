# STT AI Editor - Module 116B: Premiere Music XML Timecode Fix

Fix lỗi:

`TypeError: add_text() missing 1 required positional argument: 'text'`

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_premiere_music_xml_exporter.py
```

## Export XML lại

```powershell
python scripts/export_premiere_music_sync_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --preset vertical_1080_25p
```
