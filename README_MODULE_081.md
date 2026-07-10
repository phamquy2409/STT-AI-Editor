# STT AI Editor - Module 081: Local Command Server

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_local_command_server.py
```

## Chạy

```powershell
python scripts/start_local_command_server.py --project "D:\STT Projects\Wedding_Test_001"
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Local Command Server`

## Commit

```powershell
git status
git add core/local_command_server core/gui/local_command_server_patch.py core/gui/__init__.py scripts/start_local_command_server.py scripts/test_local_command_server.py scripts/build_exe.py README_MODULE_081.md
git commit -m "Add local command server"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
