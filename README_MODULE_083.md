# STT AI Editor - Module 083: Panel Command Bridge

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_panel_command_bridge.py
```

## Chạy

```powershell
python scripts/create_panel_command_bridge.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Panel Command Bridge`

## Commit

```powershell
git status
git add core/panel_command_bridge core/gui/panel_command_bridge_patch.py core/gui/__init__.py scripts/create_panel_command_bridge.py scripts/test_panel_command_bridge.py scripts/build_exe.py README_MODULE_083.md
git commit -m "Add panel command bridge"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
