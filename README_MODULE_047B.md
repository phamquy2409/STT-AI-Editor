# STT AI Editor - Module 047B: Compact Scroll GUI Fix

Fix giao diện bị quá dài sau khi thêm nhiều module AI/Premiere.

## Fix gì?

- Bọc toàn bộ app trong scroll area
- Cửa sổ resize được tốt hơn
- Nút nhỏ lại
- GroupBox bớt margin
- ComboBox nhỏ lại
- Có thể cuộn để xem toàn app

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/run_gui.py
```

Kết quả mong muốn:

- App không bị cao quá màn hình
- Có thể cuộn dọc
- Các nút gọn hơn
- Vẫn thấy AI Shot Scorer / Prewedding và Prewedding Learned Selector

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/gui/compact_scroll_patch.py core/gui/__init__.py scripts/build_exe.py README_MODULE_047B.md
git commit -m "Fix GUI compact scroll layout"
git push
```
