# STT AI Editor - Module 085: Auto Import Helper

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_auto_import_helper.py
```

## Chạy

```powershell
python scripts/create_auto_import_helper.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Auto Import Helper`

## Commit

```powershell
git status
git add core/auto_import_helper core/gui/auto_import_helper_patch.py core/gui/__init__.py scripts/create_auto_import_helper.py scripts/test_auto_import_helper.py scripts/build_exe.py README_MODULE_085.md
git commit -m "Add auto import helper"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
