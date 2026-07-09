# STT AI Editor - Module 071: Client Feedback Collector

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_client_feedback_collector.py
```

## Chạy

```powershell
python scripts/create_client_feedback_collector.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Client Feedback Collector`

## Commit

```powershell
git status
git add core/client_feedback core/gui/client_feedback_collector_patch.py core/gui/__init__.py scripts/create_client_feedback_collector.py scripts/test_client_feedback_collector.py scripts/build_exe.py README_MODULE_071.md
git commit -m "Add client feedback collector"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
