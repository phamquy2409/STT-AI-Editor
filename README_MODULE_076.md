# STT AI Editor - Module 076: Backup Verify Report

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_backup_verify.py
```

## Chạy

```powershell
python scripts/create_backup_verify.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Backup Verify Report`

## Commit

```powershell
git status
git add core/backup_verify core/gui/backup_verify_patch.py core/gui/__init__.py scripts/create_backup_verify.py scripts/test_backup_verify.py scripts/build_exe.py README_MODULE_076.md
git commit -m "Add backup verify report"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
