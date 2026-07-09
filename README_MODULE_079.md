# STT AI Editor - Module 079: App Log Collector

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_app_log_collector.py
```

## Chạy

```powershell
python scripts/create_app_log_collector.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`App Log Collector`

## Commit

```powershell
git status
git add core/app_log_collector core/gui/app_log_collector_patch.py core/gui/__init__.py scripts/create_app_log_collector.py scripts/test_app_log_collector.py scripts/build_exe.py README_MODULE_079.md
git commit -m "Add app log collector"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
