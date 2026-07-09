# STT AI Editor - Module 077: Project Version Tracker

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_project_version_tracker.py
```

## Chạy

```powershell
python scripts/create_project_version_tracker.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Project Version Tracker`

## Commit

```powershell
git status
git add core/project_version_tracker core/gui/project_version_tracker_patch.py core/gui/__init__.py scripts/create_project_version_tracker.py scripts/test_project_version_tracker.py scripts/build_exe.py README_MODULE_077.md
git commit -m "Add project version tracker"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
