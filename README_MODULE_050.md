# STT AI Editor - Module 050: Prewedding Smart Refiner

Module này nằm giữa 048 và 049.

## Luồng đúng

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s
python scripts/build_prewedding_selection.py --intent prewedding_reel_60s
python scripts/build_prewedding_roughcut.py --intent prewedding_reel_60s
python scripts/refine_prewedding_roughcut.py --intent prewedding_reel_60s
python scripts/export_prewedding_xml.py --preset vertical_1080_25p
```

## Module 050 làm gì?

Nó đọc:

- `stt_prewedding_roughcut_v1.json`
- `stt_prewedding_selection_v1.json`
- `stt_ai_shot_scores_v1.json`

Sau đó:

- Đưa hook mạnh nhất lên đầu
- Tránh 2 shot liền nhau cùng source
- Thay shot yếu bằng shot mạnh hơn từ score pool 046
- Cân lại section/role prewedding
- Fit duration lại cho reel/cinematic
- Ghi timeline refined để 049 export XML

## Output

Trong project:

- `stt_prewedding_refined_v1.json`
- ghi compatibility vào `stt_prewedding_selection_v1.json`

Trong export folder:

- `PREWEDDING_REFINED_TIMELINE.csv`
- `PREWEDDING_REPLACEMENT_SUGGESTIONS.csv`
- `PREWEDDING_REFINER_SUMMARY.html`
- `PREWEDDING_REFINED_EDIT_PROMPT.txt`
- `BACKUP_input_before_refine.json`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_prewedding_refiner.py
```

## Refine reel 60s

```powershell
python scripts/refine_prewedding_roughcut.py --intent prewedding_reel_60s
```

## Refine reel 30s

```powershell
python scripts/refine_prewedding_roughcut.py --intent prewedding_reel_30s
```

## Refine cinematic

```powershell
python scripts/refine_prewedding_roughcut.py --intent prewedding_cinematic
```

## Sau đó export XML bằng 049

```powershell
python scripts/export_prewedding_xml.py --preset vertical_1080_25p
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel:

`Prewedding Smart Refiner`

Có nút:

`Refine Prewedding Roughcut`

## Commit

```powershell
git status
git add core/prewedding_refiner core/gui/prewedding_refiner_patch.py core/gui/__init__.py scripts/refine_prewedding_roughcut.py scripts/test_prewedding_refiner.py scripts/build_exe.py README_MODULE_050.md
git commit -m "Add prewedding smart refiner"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
