# STT AI Editor - Module 038: Premiere XML Validator

Module này nâng cấp Premiere Bridge bằng bước kiểm tra XML trước khi import vào Premiere.

## Thêm gì?

- `Check Premiere XML` trong GUI
- `XML_VALIDATION_REPORT.html`
- `XML_VALIDATION_REPORT.txt`
- `XML_VALIDATION_REPORT.json`
- Premiere Bridge package tự kèm report kiểm tra XML

Nó kiểm tra:

- XML có parse được không
- Có sequence không
- Có clipitem không
- Có video/audio clipitem không
- Có path media không
- Media path có tồn tại không
- Cảnh báo audio trước khi import

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_premiere_xml_validator.py
```

Chạy report:

```powershell
python scripts/validate_premiere_xml.py
```

Tạo Premiere Bridge package có validator:

```powershell
python scripts/export_premiere_bridge.py
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có thêm nút:

`Check Premiere XML`

và `Premiere Bridge Package` sẽ tự tạo thêm validation report.

## Build EXE

Sau khi GUI OK:

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/premiere_bridge core/gui/premiere_xml_validator_patch.py core/gui/__init__.py scripts/validate_premiere_xml.py scripts/test_premiere_xml_validator.py scripts/build_exe.py README_MODULE_038.md
git commit -m "Add Premiere XML validator"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
