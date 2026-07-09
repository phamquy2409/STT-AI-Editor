# STT AI Editor - Module 039: Premiere JSX Helper

Module này tiến gần hơn tới tích hợp Premiere.

Nó tạo package JSX để chạy trong Premiere:

`Premiere Pro > File > Scripts > Run Script File`

Chọn:

`STT_Import_Latest_XML.jsx`

## Nó làm gì?

- Tìm XML mới nhất
- Tạo folder:

`D:\STT Projects\Wedding_Test_001\exports\premiere_jsx_helper_YYYYMMDD_HHMMSS`

Bên trong có:

- `STT_Import_Latest_XML.jsx`
- `README_RUN_IN_PREMIERE.txt`
- `Copy_JSX_Path_To_Clipboard.bat`
- `INSTALL_TO_PREMIERE_SCRIPTS_FOLDER.bat`
- `premiere_jsx_helper_manifest.json`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_premiere_jsx_helper.py
```

Tạo JSX helper:

```powershell
python scripts/create_premiere_jsx_helper.py
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có thêm nút:

`Premiere JSX Helper`

## Trong Premiere

Cách dùng:

1. Mở Premiere
2. Mở project cần dựng
3. `File > Scripts > Run Script File`
4. Chọn:

`STT_Import_Latest_XML.jsx`

Nếu không import tự động được thì dùng lại cách ổn định:

`File > Import > chọn XML`

## Lưu ý

Đây chưa phải Premiere Panel/plugin thật.

Nó là bước trung gian để gần hơn với Premiere. Plugin/panel thật nên làm sau khi core app ổn thêm.

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/premiere_bridge/jsx_helper.py core/premiere_bridge/__init__.py core/gui/premiere_jsx_helper_patch.py core/gui/__init__.py scripts/create_premiere_jsx_helper.py scripts/test_premiere_jsx_helper.py scripts/build_exe.py README_MODULE_039.md
git commit -m "Add Premiere JSX helper"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
