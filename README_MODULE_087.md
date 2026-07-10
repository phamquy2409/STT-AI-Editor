# STT AI Editor - Module 087: Panel Source Folder Config

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_panel_source_folder.py
```

## Chạy

```powershell
python scripts/create_panel_source_folder.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Panel Source Folder Config`

## Commit

```powershell
git status
git add core/panel_source_folder core/gui/panel_source_folder_patch.py core/gui/__init__.py scripts/create_panel_source_folder.py scripts/test_panel_source_folder.py scripts/build_exe.py README_MODULE_087.md
git commit -m "Add panel source folder config"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
