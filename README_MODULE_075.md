# STT AI Editor - Module 075: Archive Cleaner Plan

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_archive_cleaner_plan.py
```

## Chạy

```powershell
python scripts/create_archive_cleaner_plan.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Archive Cleaner Plan`

## Commit

```powershell
git status
git add core/archive_cleaner_plan core/gui/archive_cleaner_plan_patch.py core/gui/__init__.py scripts/create_archive_cleaner_plan.py scripts/test_archive_cleaner_plan.py scripts/build_exe.py README_MODULE_075.md
git commit -m "Add archive cleaner plan"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
