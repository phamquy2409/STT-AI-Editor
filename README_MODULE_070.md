# STT AI Editor - Module 070: Production Launcher

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_production_launcher.py
```

## Chạy

```powershell
python scripts/create_production_launcher.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Production Launcher`

## Commit

```powershell
git status
git add core/production_launcher core/gui/production_launcher_patch.py core/gui/__init__.py scripts/create_production_launcher.py scripts/test_production_launcher.py scripts/build_exe.py README_MODULE_070.md
git commit -m "Add production launcher"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
