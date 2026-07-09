# STT AI Editor - Module 011: Final Rough Cut Builder

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_final_roughcut.py
```

What it does:

- reads latest `roughcut_plan_people_composition.json`
- selects best clips using:
  - final_wedding_score
  - best_moment_score
  - ai_keep_score
- rebuilds timeline order
- creates a new final folder:
  - `D:\STT Projects\Wedding_Test_001\exports\final_roughcut_YYYYMMDD_HHMMSS`
- exports:
  - roughcut_final.json
  - roughcut_final.csv
  - final_roughcut_summary.txt
  - stt_ai_premiere_import.xml
  - review.html

Manual command:

```powershell
python main.py final-roughcut --project "D:\STT Projects\Wedding_Test_001" --target-duration 60 --min-final-score 20
```

Then import the XML into Premiere:

`File > Import > stt_ai_premiere_import.xml`
