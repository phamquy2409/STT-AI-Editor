# STT AI Editor - Module 040: Premiere Script Installer

Module này đưa app tiến gần hơn tới tích hợp Premiere.

Thay vì mỗi lần tạo JSX mới, bản này cài một script ổn định cho Premiere:

`STT_Import_Latest_XML.jsx`

Script này đọc đường dẫn XML mới nhất từ:

`%APPDATA%\STT_AI_Editor\premiere_latest_xml.txt`

Như vậy sau này app chỉ cần update file pointer, script trong Premiere có thể giữ nguyên.

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_premiere_script_installer.py
```

Cài / tạo package:

```powershell
python scripts/install_premiere_script.py
```

Nó sẽ tạo folder:

`D:\STT Projects\Wedding_Test_001\exports\premiere_script_installer_YYYYMMDD_HHMMSS`

Trong đó có:

- `STT_Import_Latest_XML.jsx`
- `STT_Open_Latest_XML_Folder.jsx`
- `INSTALL_TO_PREMIERE_MENU.bat`
- `Update_Latest_XML_Path.bat`
- `README_PREMIERE_SCRIPT_INSTALL.txt`

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có thêm nút:

`Install Premiere Script`

## Trong Premiere

Sau khi cài thành công vào Program Files:

1. Restart Premiere
2. Mở project
3. Vào:

`File > Scripts > STT_Import_Latest_XML`

Nếu không thấy script trong menu:

- Chạy `INSTALL_TO_PREMIERE_MENU.bat` bằng `Run as Administrator`
- Hoặc dùng:

`File > Scripts > Run Script File`

và chọn file JSX trong package.

## Lưu ý

Đây chưa phải Premiere Panel/plugin thật.

Nhưng đây là mức tích hợp tốt hơn Module 039 vì script có thể giữ cố định trong Premiere, còn STT AI Editor chỉ update latest XML pointer.

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/premiere_bridge/script_installer.py core/premiere_bridge/__init__.py core/gui/premiere_script_installer_patch.py core/gui/__init__.py scripts/install_premiere_script.py scripts/test_premiere_script_installer.py scripts/build_exe.py README_MODULE_040.md
git commit -m "Add Premiere script installer"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
