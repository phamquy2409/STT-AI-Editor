# STT AI Editor - Module 068: Timeline QC Report

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_timeline_qc.py
```

## Chạy

```powershell
python scripts/create_timeline_qc.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Timeline QC Report`

## Commit

```powershell
git status
git add core/timeline_qc core/gui/timeline_qc_patch.py core/gui/__init__.py scripts/create_timeline_qc.py scripts/test_timeline_qc.py scripts/build_exe.py README_MODULE_068.md
git commit -m "Add timeline QC report"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
