# STT AI Editor - Module 024: Wedding Pipeline V2

This module runs the smarter wedding pipeline in one command:

1. Wedding Scene Classifier
2. Story Timeline V2
3. Duplicate Shot Remover
4. Premiere XML Export
5. review.html
6. manual_review.html

Copy into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_wedding_pipeline_v2.py
```

Output log:

`D:\STT Projects\Wedding_Test_001\exports\wedding_pipeline_v2_YYYYMMDD_HHMMSS`

Final working output is inside:

`D:\STT Projects\Wedding_Test_001\exports\duplicate_removed_YYYYMMDD_HHMMSS`

Files:

- `roughcut_no_duplicates.json`
- `stt_ai_premiere_import.xml`
- `review.html`
- `manual_review.html`

Then:

1. Import `stt_ai_premiere_import.xml` into Premiere
2. Check if the timeline is better
3. Use manual review if needed
