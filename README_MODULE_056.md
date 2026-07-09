# STT AI Editor - Module 056: Premiere Relink Helper

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_premiere_relink_helper.py
```

## Chạy

```powershell
python scripts/create_premiere_relink_report.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút: **Premiere Relink Helper**.

## Commit

```powershell
git status
git add core/premiere_relink_helper core/gui/premiere_relink_helper_patch.py core/gui/__init__.py scripts/create_premiere_relink_report.py scripts/test_premiere_relink_helper.py scripts/build_exe.py README_MODULE_056.md
git commit -m "Add Premiere relink helper"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
