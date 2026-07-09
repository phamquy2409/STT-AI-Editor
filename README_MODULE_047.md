# STT AI Editor - Module 047: Prewedding Learned Selector

Module này dùng điểm từ Module 046 để chọn shot và tạo timeline rough cut prewedding/reel.

## Input

- `stt_ai_shot_scores_v1.json`
- Hoặc latest score export trong `exports`
- Nếu chưa có score, module sẽ cố tự chạy Module 046 trước.

## Output

Tạo:

`D:\STT Projects\Wedding_Test_001\stt_prewedding_selection_v1.json`

và copy sang:

`%APPDATA%\STT_AI_Editor\stt_prewedding_selection_v1.json`

Trong export folder có:

- `PREWEDDING_TIMELINE.csv`
- `PREWEDDING_SELECTED_SHOTS.csv`
- `PREWEDDING_SELECTOR_SUMMARY.html`
- `PREWEDDING_EDIT_PROMPT.txt`
- `stt_prewedding_selection_v1.json`

## Intent hỗ trợ

- `prewedding_reel_30s`
- `prewedding_reel_60s`
- `prewedding_cinematic`
- `prewedding_fashion`
- `prewedding_location_film`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_prewedding_selector.py
```

## Chạy reel 60s

```powershell
python scripts/build_prewedding_selection.py --intent prewedding_reel_60s
```

## Chạy reel 30s

```powershell
python scripts/build_prewedding_selection.py --intent prewedding_reel_30s
```

## Chạy cinematic

```powershell
python scripts/build_prewedding_selection.py --intent prewedding_cinematic
```

## Chỉnh duration thủ công

```powershell
python scripts/build_prewedding_selection.py --intent prewedding_reel_60s --duration 45
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel:

`Prewedding Learned Selector`

Có dropdown chọn intent và nút:

`Build Prewedding Selection`

## Workflow đúng

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s
python scripts/build_prewedding_selection.py --intent prewedding_reel_60s
```

Sau đó mở report HTML để xem shot đã chọn.

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/prewedding_selector core/gui/prewedding_selector_patch.py core/gui/__init__.py scripts/build_prewedding_selection.py scripts/test_prewedding_selector.py scripts/build_exe.py README_MODULE_047.md
git commit -m "Add prewedding learned selector"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`

## Module kế tiếp

048: tạo roughcut prewedding/reel từ selection này.

049: xuất XML 9:16/16:9 tối ưu cho Premiere.
