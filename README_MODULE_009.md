# STT AI Editor - Module 009: Best Moment Finder

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_best_moment_finder.py
```

What it does:

- Reads latest `roughcut_plan.json`
- Scans each selected roughcut segment every 0.25s
- Finds the best frame/second inside each segment
- Refines each selected range to around 2.2s
- Creates a new review.html from the refined plan

Output files:

- roughcut_plan_best_moments.json
- roughcut_plan_best_moments.csv
- best_moment_summary.txt
- review.html

Manual command:

```powershell
python main.py best-moments --project "D:\STT Projects\Wedding_Test_001" --segment-seconds 2.2 --sample-step 0.25
```
