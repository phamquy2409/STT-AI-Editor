# STT AI Editor - Module 037: Premiere Bridge

Module này tạo cầu nối sạch hơn giữa STT AI Editor và Premiere.

Nó chưa phải plugin panel trong Premiere, nhưng là bước đúng để đi tới tích hợp thật.

## Nó làm gì?

Tìm XML mới nhất:

`D:\STT Projects\Wedding_Test_001\exports\**\stt_ai_premiere_import.xml`

Rồi tạo package:

`D:\STT Projects\Wedding_Test_001\exports\premiere_bridge_YYYYMMDD_HHMMSS\`

Bên trong có:

- `01_STT_AI_Premiere_Import.xml`
- `README_IMPORT_PREMIERE.txt`
- `PREMIERE_IMPORT_STEPS.html`
- `premiere_import_helper.jsx`
- `Copy_XML_Path_To_Clipboard.bat`
- `premiere_bridge_manifest.json`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_premiere_bridge.py
```

Tạo package:

```powershell
python scripts/export_premiere_bridge.py
```

## Trong GUI

Mở:

```powershell
python scripts/run_gui.py
```

Trong panel Production sẽ có nút:

`Premiere Bridge Package`

Bấm nút đó sau khi đã export XML.

## Import vào Premiere

Cách ổn định nhất:

1. Mở Premiere Pro
2. Mở project cần dựng
3. `File > Import`
4. Chọn:

`01_STT_AI_Premiere_Import.xml`

## JSX helper

File `premiere_import_helper.jsx` có thể thử bằng:

`Premiere > File > Scripts > Run Script File`

Nhưng đây chỉ là helper thử nghiệm. Tùy phiên bản Premiere, import XML tự động bằng script có thể bị giới hạn.

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/premiere_bridge core/gui/premiere_bridge_patch.py core/gui/__init__.py scripts/export_premiere_bridge.py scripts/test_premiere_bridge.py scripts/build_exe.py README_MODULE_037.md
git commit -m "Add Premiere Bridge export package"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
