# STT AI Editor - Module 072: Client Select Sync

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_client_select_sync.py
```

## Chạy

```powershell
python scripts/create_client_select_sync.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Client Select Sync`

## Commit

```powershell
git status
git add core/client_select_sync core/gui/client_select_sync_patch.py core/gui/__init__.py scripts/create_client_select_sync.py scripts/test_client_select_sync.py scripts/build_exe.py README_MODULE_072.md
git commit -m "Add client select sync plan"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
