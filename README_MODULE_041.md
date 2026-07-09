# STT AI Editor - Module 041: Premiere Panel Starter

Đây là bước đầu tiên làm panel thật trong Premiere.

Module này tạo CEP panel:

`Premiere Pro > Window > Extensions > STT AI Editor`

Panel có nút:

- `Refresh Latest XML`
- `Import Latest XML`
- `Open XML Folder`

Panel đọc XML mới nhất từ Module 040:

`%APPDATA%\STT_AI_Editor\premiere_latest_xml.txt`

## Cài module vào app

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test Python

```powershell
python scripts/test_premiere_panel.py
```

## Tạo / cài panel

```powershell
python scripts/create_premiere_panel.py
```

Nó sẽ tạo folder:

`D:\STT Projects\Wedding_Test_001\exports\premiere_panel_starter_YYYYMMDD_HHMMSS`

Trong đó có:

- `com.stt.ai.editor.panel`
- `INSTALL_PANEL_TO_USER_CEP.bat`
- `ENABLE_CEP_DEBUG_MODE.bat`
- `UNINSTALL_PANEL_FROM_USER_CEP.bat`
- `README_INSTALL_PREMIERE_PANEL.txt`

## Mở trong Premiere

Sau khi chạy create panel:

1. Chạy `ENABLE_CEP_DEBUG_MODE.bat`
2. Chạy `INSTALL_PANEL_TO_USER_CEP.bat`
3. Restart Premiere Pro
4. Mở:

`Window > Extensions > STT AI Editor`

## Nếu không thấy panel

- Chạy lại `ENABLE_CEP_DEBUG_MODE.bat`
- Restart Premiere
- Kiểm tra folder:

`%APPDATA%\Adobe\CEP\extensions\com.stt.ai.editor.panel`

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có nút mới:

`Create Premiere Panel`

## Lưu ý

Đây là panel starter đầu tiên, chưa phải plugin đóng gói chính thức.

Nếu import XML từ panel không chạy, dùng cách chắc chắn:

`Premiere > File > Import > chọn XML`

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/premiere_bridge/panel_installer.py core/premiere_bridge/__init__.py core/gui/premiere_panel_patch.py core/gui/__init__.py scripts/create_premiere_panel.py scripts/test_premiere_panel.py scripts/build_exe.py README_MODULE_041.md
git commit -m "Add Premiere panel starter"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
