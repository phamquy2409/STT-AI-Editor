# STT AI Editor - Module 023: Duplicate Shot Remover

Goal:
Remove repeated / near-repeated shots after Story Timeline V2.

It checks:

- same source video with close timestamps
- similar thumbnail visual hash
- similar color histogram
- same wedding_scene label
- too many segments from same source video

Copy into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_duplicate_shot_remover.py
```

Output:

`D:\STT Projects\Wedding_Test_001\exports\duplicate_removed_YYYYMMDD_HHMMSS`

Files:

- `roughcut_no_duplicates.json`
- `roughcut_no_duplicates.csv`
- `roughcut_plan.json`
- `duplicate_removed.csv`
- `duplicate_removed_summary.txt`
- `stt_ai_premiere_import.xml`
- `review.html`
- `manual_review.html`

Then import XML into Premiere.

Note:
If it removes too much, it fills back from the latest `wedding_scene_...` candidate pool.
