# STT AI Editor - Module 054: Pipeline Snapshot

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_pipeline_snapshot.py
```

## Chạy

```powershell
python scripts/create_pipeline_snapshot.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút: **Pipeline Snapshot**.

## Commit

```powershell
git status
git add core/pipeline_snapshot core/gui/pipeline_snapshot_patch.py core/gui/__init__.py scripts/create_pipeline_snapshot.py scripts/test_pipeline_snapshot.py scripts/build_exe.py README_MODULE_054.md
git commit -m "Add pipeline snapshot tool"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
