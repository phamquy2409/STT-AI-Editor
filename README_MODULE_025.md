# STT AI Editor - Module 025: GUI Wedding Pipeline V2

Adds a new GUI button:

`Run Wedding Pipeline V2`

This runs:

1. Wedding Scene Classifier
2. Story Timeline V2
3. Duplicate Shot Remover
4. Premiere XML
5. Review HTML
6. Manual Review HTML

Copy into:

`D:\Projects\STT-AI-Editor`

Run GUI:

```powershell
python scripts/run_gui.py
```

Use:

1. Open GUI
2. Keep Active Project:
   `D:\STT Projects\Wedding_Test_001`
3. Click:
   `Run Wedding Pipeline V2`
4. Wait for `manual_review.html`
5. Import latest `stt_ai_premiere_import.xml` into Premiere

Notes:

- `Run Pipeline Old` is the old 016 pipeline.
- `Run Wedding Pipeline V2` is the newer 021 → 022 → 023 → XML pipeline.
- Wedding Pipeline V2 does not scan/detect/analyze again.
