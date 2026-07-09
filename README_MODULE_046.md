# STT AI Editor - Module 046: AI Shot Scorer V1 + Prewedding

Module này bắt đầu cho AI chấm điểm shot theo gu dựng.

Quan trọng: module này đã bổ sung prewedding.

## Intent có sẵn

Prewedding:

- `prewedding_cinematic`
- `prewedding_reel_30s`
- `prewedding_reel_60s`
- `prewedding_fashion`
- `prewedding_location_film`

Wedding:

- `wedding_teaser_60s`
- `wedding_highlight_3min`
- `review_culling`

## Module này làm gì?

Nó đọc:

- `manual_selection.json`
- `stt_ai_style_memory_v2.json`
- `stt_wedding_style_profile.json`
- `stt_feedback_profile.json`
- các candidate JSON trong `exports`

Sau đó tạo:

- `stt_ai_shot_scores_v1.json`
- `AI_SHOT_SCORES.csv`
- `AI_SELECTED_TOP_SHOTS.csv`
- report HTML/TXT

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_ai_shot_scorer.py
```

## Chạy prewedding reel 60s

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s
```

## Chạy prewedding reel 30s

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_30s
```

## Chạy prewedding cinematic

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_cinematic
```

## Chạy prewedding fashion

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_fashion
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel mới:

`AI Shot Scorer / Prewedding`

Có dropdown chọn intent và nút:

`Run AI Shot Scorer V1`

## Prewedding ưu tiên

- couple đẹp
- đi bộ
- nắm tay
- nhìn nhau
- ôm
- váy bay / xoay váy
- close-up
- location đẹp
- slow motion
- fashion pose
- shot có chuyển động mượt

## Prewedding reel ưu tiên

- 9:16
- hook 1-3 giây đầu
- shot đẹp nhất lên đầu
- cut nhanh theo beat
- fashion / motion / close-up / location
- tránh kể chuyện dài

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/ai_shot_scorer core/gui/ai_shot_scorer_patch.py core/gui/__init__.py scripts/run_ai_shot_scorer.py scripts/test_ai_shot_scorer.py scripts/build_exe.py README_MODULE_046.md
git commit -m "Add AI shot scorer with prewedding intents"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`

## Module kế tiếp

047 nên làm:

`Prewedding Learned Selector`

Tức là dùng điểm từ Module 046 để chọn top shot và bắt đầu tạo rough cut prewedding/reel.
