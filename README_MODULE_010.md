# STT AI Editor - Module 010: People / Face / Composition Scoring

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_people_composition.py
```

What it does:

- reads latest `roughcut_plan_best_moments.json`
- detects faces using OpenCV Haar cascades
- estimates subject/detail/composition score
- labels shot type:
  - face_people
  - wide_people
  - possible_people_or_detail
  - empty_or_decor
- writes:
  - roughcut_plan_people_composition.json
  - roughcut_plan_people_composition.csv
  - people_composition_summary.txt
- regenerates review.html from the ranked people/composition plan

Manual command:

```powershell
python main.py people-composition --project "D:\STT Projects\Wedding_Test_001"
```

Note: this is still lightweight OpenCV detection, not full wedding semantic AI yet.
