# STT AI Editor - Module 026: GUI Direct Manual Save

Adds GUI buttons for Module 020 Live Manual Review:

- `Open Live Manual Review`
- `Stop Live Server`
- `Export Latest Manual XML`

New workflow:

1. Run `Wedding Pipeline V2`
2. Click `Open Live Manual Review`
3. In browser: KEEP / REJECT
4. Click `Save to Project Folder`
5. Back to GUI: click `Export Latest Manual XML`
6. Click `Open Latest XML Folder`
7. Import `stt_ai_premiere_import.xml` into Premiere

Copy into:

`D:\Projects\STT-AI-Editor`

Run GUI:

```powershell
python scripts/run_gui.py
```

Important:

- This module needs Module 020 file:
  `scripts/run_live_manual_review.py`
- Default local server:
  `http://127.0.0.1:8787`
- If port 8787 is busy, change the port number in GUI, for example 8788.
