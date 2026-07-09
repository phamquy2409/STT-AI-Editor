# STT AI Editor - Module 014: Manual Review KEEP / MAYBE / REJECT

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_manual_review.py
```

What it creates in latest story/final folder:

- `manual_review.html`
- `manual_selection_template.json`
- `manual_selection_template.csv`
- `manual_review_instruction.txt`

Use:

1. Open `manual_review.html`
2. Click `KEEP`, `MAYBE`, or `REJECT`
3. Click `Export JSON` or `Export CSV`
4. Browser downloads:
   - `manual_selection.json`
   - `manual_selection.csv`

Important:
Browser security does not allow local HTML to silently write the edited JSON back into the project folder.
The exported file usually goes to Downloads.

Module 015 will use `manual_selection.json` to rebuild Premiere XML from your manual choices.

Manual command:

```powershell
python main.py manual-review --project "D:\STT Projects\Wedding_Test_001"
```
