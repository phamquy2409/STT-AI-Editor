# STT AI Editor - Module 028: GUI Settings Persistence

Adds saved GUI settings.

The app now remembers:

- Projects root
- Project name
- Active project folder
- Source folder
- Target duration
- Top candidates
- Live Manual Review port
- Window size

Settings file on Windows:

`%APPDATA%\STT_AI_Editor\gui_settings.json`

New buttons:

- `Save Settings`
- `Reset Settings`
- `Open Settings Folder`

Copy into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/run_gui.py
```

Test:

1. Change Project folder or Source folder
2. Click `Save Settings`
3. Close GUI
4. Reopen GUI
5. Values should stay the same
