# STT AI Editor - Module 067: Source Media Audit

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_source_media_audit.py
```

## Chạy

```powershell
python scripts/create_source_media_audit.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Source Media Audit`

## Commit

```powershell
git status
git add core/source_media_audit core/gui/source_media_audit_patch.py core/gui/__init__.py scripts/create_source_media_audit.py scripts/test_source_media_audit.py scripts/build_exe.py README_MODULE_067.md
git commit -m "Add source media audit"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
