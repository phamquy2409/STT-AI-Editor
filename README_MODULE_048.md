# STT AI Editor - Module 048: Prewedding Roughcut Builder

Module này nằm giữa 047 và 049.

## Luồng đúng

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s
python scripts/build_prewedding_selection.py --intent prewedding_reel_60s
python scripts/build_prewedding_roughcut.py --intent prewedding_reel_60s
python scripts/export_prewedding_xml.py --preset vertical_1080_25p
```

## Module 048 làm gì?

Nó đọc:

`stt_prewedding_selection_v1.json`

Sau đó tạo roughcut tốt hơn:

`stt_prewedding_roughcut_v1.json`

và đồng thời ghi compatibility trở lại:

`stt_prewedding_selection_v1.json`

để Module 049 export XML dùng timeline roughcut này luôn.

## Output

Trong export folder có:

- `stt_prewedding_roughcut_v1.json`
- `PREWEDDING_ROUGHCUT_TIMELINE.csv`
- `PREWEDDING_ROUGHCUT_SUMMARY.html`
- `PREWEDDING_ROUGHCUT_EDIT_PROMPT.txt`
- `BACKUP_original_stt_prewedding_selection_v1.json`

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
python scripts/test_prewedding_roughcut.py
```

## Build roughcut reel 60s

```powershell
python scripts/build_prewedding_roughcut.py --intent prewedding_reel_60s
```

## Build roughcut cinematic

```powershell
python scripts/build_prewedding_roughcut.py --intent prewedding_cinematic
```

## Chỉnh duration thủ công

```powershell
python scripts/build_prewedding_roughcut.py --intent prewedding_reel_60s --duration 45
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel:

`Prewedding Roughcut Builder`

Có dropdown chọn intent và nút:

`Build Prewedding Roughcut`

## Sau đó xuất XML bằng 049

```powershell
python scripts/export_prewedding_xml.py --preset vertical_1080_25p
```

## Commit

```powershell
git status
git add core/prewedding_roughcut core/gui/prewedding_roughcut_patch.py core/gui/__init__.py scripts/build_prewedding_roughcut.py scripts/test_prewedding_roughcut.py scripts/build_exe.py README_MODULE_048.md
git commit -m "Add prewedding roughcut builder"
git push
```

Nếu đã cài 049 rồi, có thể commit gộp 048 + 049.
