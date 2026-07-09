# STT AI Editor - Module 006: Rough Cut Builder

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_roughcut_builder.py
```

Or:

```powershell
python main.py roughcut --project "D:\STT Projects\Wedding_Test_001" --target-duration 60 --min-keep-score 45 --max-segments-per-video 2
```

Output folder:

`D:\STT Projects\Wedding_Test_001\exports\roughcut_YYYYMMDD_HHMMSS`

Generated:

- roughcut_plan.csv
- roughcut_plan.json
- roughcut_summary.txt
- roughcut_premiere_experimental.xml

Open `roughcut_plan.csv` first. It is the safe source of truth.

The XML is experimental and will be improved in the next Premiere Export module.
