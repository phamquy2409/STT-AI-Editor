# STT AI Editor - Module 029: Clean / Archive Exports

Adds safe export cleanup.

It does NOT delete anything.

It moves old export folders into:

`D:\STT Projects\Wedding_Test_001\exports\_archive\archive_YYYYMMDD_HHMMSS`

New GUI section:

`Clean / Archive Exports`

Buttons:

- `Preview Cleanup`
- `Archive Old Exports`
- `Open Archive`
- `Open Cleanup Reports`

Default:

- Keep latest 2 folders per export type
- Archive older folders

Copy into:

`D:\Projects\STT-AI-Editor`

Run GUI:

```powershell
python scripts/run_gui.py
```

Test:

1. Click `Preview Cleanup`
2. Check cleanup report
3. If OK, click `Archive Old Exports`

CLI preview:

```powershell
python scripts/test_export_cleaner.py
```

CLI archive:

```powershell
python scripts/archive_old_exports.py
```
