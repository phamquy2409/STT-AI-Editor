# STT AI Editor - Module 074: Export Version Namer

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_export_version_namer.py
```

## Chạy

```powershell
python scripts/create_export_version_namer.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Export Version Namer`

## Commit

```powershell
git status
git add core/export_version_namer core/gui/export_version_namer_patch.py core/gui/__init__.py scripts/create_export_version_namer.py scripts/test_export_version_namer.py scripts/build_exe.py README_MODULE_074.md
git commit -m "Add export version namer"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
