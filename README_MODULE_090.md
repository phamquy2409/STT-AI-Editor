# STT AI Editor - Module 090: Background App Start Helper

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_background_app_start_helper.py
```

## Chạy

```powershell
python scripts/create_background_app_start_helper.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Background App Start Helper`

## Commit

```powershell
git status
git add core/background_app_start_helper core/gui/background_app_start_helper_patch.py core/gui/__init__.py scripts/create_background_app_start_helper.py scripts/test_background_app_start_helper.py scripts/build_exe.py README_MODULE_090.md
git commit -m "Add background app start helper"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
