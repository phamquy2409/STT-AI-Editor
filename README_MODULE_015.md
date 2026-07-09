# STT AI Editor - Module 015: Manual Selection to Premiere XML

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_manual_selection_export.py
```

Before running:
1. Open `manual_review.html`
2. Mark shots as KEEP / MAYBE / REJECT
3. Click `Export JSON`
4. Keep the downloaded file named `manual_selection.json`

By default this module looks for the newest:

- `Downloads\manual_selection.json`
- `Downloads\manual_selection*.json`
- project export folders

What it does:

- reads `manual_selection.json`
- uses KEEP shots only
- if no KEEP exists, it falls back to MAYBE
- excludes REJECT
- rebuilds timeline order
- exports:
  - manual_roughcut.json
  - roughcut_plan.json
  - stt_ai_premiere_import.xml
  - review.html

Manual command:

```powershell
python main.py manual-export --project "D:\STT Projects\Wedding_Test_001"
```

Or specify exact file:

```powershell
python main.py manual-export --project "D:\STT Projects\Wedding_Test_001" --selection-json "C:\Users\YOURNAME\Downloads\manual_selection.json"
```
