# STT AI Editor - Module 043: Premiere Panel Sync

Module này làm bước sync rõ ràng giữa STT app và panel Premiere.

## Thêm gì?

- `Sync Premiere Panel` trong GUI
- `scripts/sync_premiere_panel.py`
- `premiere_panel_status.json`
- `premiere_panel_sync_...` report folder
- Panel Premiere mới có:
  - Sync status
  - Validation status
  - Open Sync Report
- Create Premiere Panel tự sync trước khi cài panel

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_premiere_panel_sync.py
```

Chạy sync:

```powershell
python scripts/sync_premiere_panel.py
```

## Tạo lại panel mới

```powershell
python scripts/create_premiere_panel.py
```

Trong folder vừa mở:

1. Chạy `ENABLE_CEP_DEBUG_MODE.bat`
2. Chạy `INSTALL_PANEL_TO_USER_CEP.bat`
3. Restart Premiere
4. `Window > Extensions > STT AI Editor`

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có thêm nút:

`Sync Premiere Panel`

Workflow:

1. `Export Latest Manual XML`
2. `Sync Premiere Panel`
3. Qua Premiere panel bấm `Refresh Latest XML`
4. Bấm `Import Latest XML`

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/premiere_bridge/panel_sync.py core/premiere_bridge/panel_installer.py core/premiere_bridge/bridge.py core/premiere_bridge/__init__.py core/gui/premiere_panel_sync_patch.py core/gui/__init__.py scripts/sync_premiere_panel.py scripts/test_premiere_panel_sync.py scripts/build_exe.py README_MODULE_043.md
git commit -m "Add Premiere panel sync workflow"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
