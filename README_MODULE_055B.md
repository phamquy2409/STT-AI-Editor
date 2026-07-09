# STT AI Editor - Module 055B: Fix Prewedding Batch Plan Button

Bản fix này sửa lỗi GUI import nhầm:

- Sai: `prewedding_batch_patch`
- Đúng: `prewedding_batch_plan_patch`

Sau khi cài, app sẽ hiện thêm panel:

`Prewedding Batch Plan`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/run_gui.py
```

Kéo xuống sẽ thấy:

`Prewedding Batch Plan`

## Commit

```powershell
git status
git add core/gui/__init__.py scripts/build_exe.py README_MODULE_055B.md
git commit -m "Fix prewedding batch plan GUI import"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
