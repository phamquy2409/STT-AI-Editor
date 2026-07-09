# STT AI Editor - Module 005: Report / Ranking

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_report_generator.py
```

Or:

```powershell
python main.py report --project "D:\STT Projects\Wedding_Test_001" --limit 200 --min-keep-score 45
```

Output folder:

`D:\STT Projects\Wedding_Test_001\reports\report_YYYYMMDD_HHMMSS`

Generated files:

- summary.txt
- summary.json
- top_keep_segments.csv
- roughcut_candidates.csv
- low_quality_segments.csv
- blurry_segments.csv
- shaky_segments.csv
- exposure_problem_segments.csv

Open the CSV files in Excel to inspect whether Vision scoring is reasonable.
