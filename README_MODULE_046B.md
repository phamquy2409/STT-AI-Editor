# STT AI Editor - Module 046B: Fix AI Shot Scorer load_json

Fix lỗi:

`AttributeError: 'AIShotScorerV1' object has no attribute 'load_json_first'`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test lại

```powershell
python scripts/test_ai_shot_scorer.py
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s
```

## Commit

```powershell
git status
git add core/ai_shot_scorer/scorer.py README_MODULE_046B.md
git commit -m "Fix AI shot scorer JSON loading"
git push
```
