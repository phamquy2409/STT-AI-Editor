# STT AI Editor - Module 089: Panel Error Reporter

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_panel_error_reporter.py
```

## Chạy

```powershell
python scripts/create_panel_error_reporter.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Panel Error Reporter`

## Commit

```powershell
git status
git add core/panel_error_reporter core/gui/panel_error_reporter_patch.py core/gui/__init__.py scripts/create_panel_error_reporter.py scripts/test_panel_error_reporter.py scripts/build_exe.py README_MODULE_089.md
git commit -m "Add panel error reporter"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
