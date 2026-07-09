# STT AI Editor - Module 078: Smart Folder Organizer

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_smart_folder_organizer.py
```

## Chạy

```powershell
python scripts/create_smart_folder_organizer.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Smart Folder Organizer`

## Commit

```powershell
git status
git add core/smart_folder_organizer core/gui/smart_folder_organizer_patch.py core/gui/__init__.py scripts/create_smart_folder_organizer.py scripts/test_smart_folder_organizer.py scripts/build_exe.py README_MODULE_078.md
git commit -m "Add smart folder organizer"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
