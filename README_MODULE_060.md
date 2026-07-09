# STT AI Editor - Module 060: Master Dashboard

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_master_dashboard.py
```

## Chạy

```powershell
python scripts/create_master_dashboard.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút: **Master Dashboard**.

## Commit

```powershell
git status
git add core/master_dashboard core/gui/master_dashboard_patch.py core/gui/__init__.py scripts/create_master_dashboard.py scripts/test_master_dashboard.py scripts/build_exe.py README_MODULE_060.md
git commit -m "Add master dashboard"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
