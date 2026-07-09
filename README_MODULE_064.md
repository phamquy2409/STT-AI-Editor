# STT AI Editor - Module 064: SFX Placeholder Manager

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_sfx_placeholder_manager.py
```

## Chạy

```powershell
python scripts/create_sfx_placeholder_manager.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`SFX Placeholder Manager`

## Commit

```powershell
git status
git add core/sfx_placeholder core/gui/sfx_placeholder_manager_patch.py core/gui/__init__.py scripts/create_sfx_placeholder_manager.py scripts/test_sfx_placeholder_manager.py scripts/build_exe.py README_MODULE_064.md
git commit -m "Add SFX placeholder manager"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
