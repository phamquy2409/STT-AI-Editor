# STT AI Editor - Module 021: Wedding Scene Classifier

Adds lightweight wedding-scene labels:

- bride_groom
- family
- ceremony
- stage
- guest
- decor
- wide_establishing
- detail
- party
- unknown

Copy into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_wedding_scene_classifier.py
```

Output folder:

`D:\STT Projects\Wedding_Test_001\exports\wedding_scene_YYYYMMDD_HHMMSS`

Files:

- `roughcut_wedding_scene.json`
- `roughcut_wedding_scene.csv`
- `roughcut_plan.json`
- `wedding_scene_summary.txt`

Important:
This is not a heavy AI model yet. It is a wedding-specific heuristic classifier using existing scores and thumbnail image features.

Next module can use these labels to build better wedding story timelines.
