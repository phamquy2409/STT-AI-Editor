# STT AI Editor - Module 051: Prewedding One-Click Pipeline

Module này gộp full luồng prewedding vào 1 lệnh.

## Luồng cũ

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s
python scripts/build_prewedding_selection.py --intent prewedding_reel_60s
python scripts/build_prewedding_roughcut.py --intent prewedding_reel_60s
python scripts/refine_prewedding_roughcut.py --intent prewedding_reel_60s
python scripts/export_prewedding_xml.py --preset vertical_1080_25p
```

## Luồng mới

```powershell
python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s
```

Nó tự chạy:

- 046 AI Shot Scorer
- 047 Prewedding Selector
- 048 Prewedding Roughcut
- 050 Prewedding Smart Refiner
- 049 Prewedding XML Export

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test import

```powershell
python scripts/test_prewedding_pipeline.py
```

## Chạy full reel 60s

```powershell
python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s
```

## Chạy full reel 30s

```powershell
python scripts/run_prewedding_pipeline.py --intent prewedding_reel_30s
```

## Chạy full cinematic ngang

```powershell
python scripts/run_prewedding_pipeline.py --intent prewedding_cinematic
```

## Custom duration

```powershell
python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s --duration 45
```

## Custom XML preset

```powershell
python scripts/run_prewedding_pipeline.py --intent prewedding_cinematic --preset fhd_1080_25p
```

## Output

Trong project:

- `stt_prewedding_pipeline_v1.json`

Trong export folder:

- `PREWEDDING_PIPELINE_SUMMARY.html`
- `PREWEDDING_PIPELINE_SUMMARY.txt`
- `stt_prewedding_pipeline_v1.json`

Sau khi chạy xong, XML đã được update vào Premiere pointer:

`%APPDATA%\STT_AI_Editor\premiere_latest_xml.txt`

## Import Premiere

Cách 1:

- Premiere > Window > Extensions > STT AI Editor
- Refresh Latest XML
- Import Latest XML

Cách 2:

- Premiere > File > Import > chọn XML

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel mới:

`Prewedding One-Click Pipeline`

Có nút:

`Run Full Prewedding Pipeline`

## Commit

```powershell
git status
git add core/prewedding_pipeline core/gui/prewedding_pipeline_patch.py core/gui/__init__.py scripts/run_prewedding_pipeline.py scripts/test_prewedding_pipeline.py scripts/build_exe.py README_MODULE_051.md
git commit -m "Add one-click prewedding pipeline"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
