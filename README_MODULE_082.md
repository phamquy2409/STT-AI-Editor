# STT AI Editor - Module 082: Premiere Panel Run Buttons

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_premiere_panel_run_buttons.py
```

## Chạy

```powershell
python scripts/create_premiere_panel_run_buttons.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Premiere Panel Run Buttons`

## Commit

```powershell
git status
git add core/premiere_panel_run_buttons core/gui/premiere_panel_run_buttons_patch.py core/gui/__init__.py scripts/create_premiere_panel_run_buttons.py scripts/test_premiere_panel_run_buttons.py scripts/build_exe.py README_MODULE_082.md
git commit -m "Add Premiere panel run buttons"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
