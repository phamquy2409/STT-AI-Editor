# STT AI Editor - Module 042: Premiere Panel Polish + Auto Pointer

Module này nâng cấp phần Premiere panel:

- Panel trong Premiere đẹp và rõ trạng thái hơn
- Có kiểm tra XML tồn tại hay không
- Có `premiere_latest_xml.json`
- Có nút trong STT app: `Update Premiere XML Pointer`
- Premiere Bridge tự update pointer
- Create Premiere Panel tự update pointer

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test pointer

```powershell
python scripts/test_premiere_pointer.py
```

Update pointer thủ công:

```powershell
python scripts/update_premiere_xml_pointer.py
```

## Tạo lại panel 042

```powershell
python scripts/create_premiere_panel.py
```

Sau đó trong folder vừa mở:

1. Chạy `ENABLE_CEP_DEBUG_MODE.bat`
2. Chạy `INSTALL_PANEL_TO_USER_CEP.bat`
3. Restart Premiere
4. Mở:

`Window > Extensions > STT AI Editor`

Panel sẽ có giao diện mới hơn:

- Refresh Latest XML
- Import Latest XML
- Open XML Folder
- Reveal in Project Panel
- Trạng thái Exists / Updated

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có thêm nút:

`Update Premiere XML Pointer`

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/premiere_bridge/pointer.py core/premiere_bridge/panel_installer.py core/premiere_bridge/bridge.py core/premiere_bridge/__init__.py core/gui/premiere_pointer_patch.py core/gui/__init__.py scripts/update_premiere_xml_pointer.py scripts/test_premiere_pointer.py scripts/build_exe.py README_MODULE_042.md
git commit -m "Polish Premiere panel and add XML pointer updater"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
