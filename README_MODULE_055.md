# STT AI Editor - Module 055: Prewedding Batch Plan

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_prewedding_batch_plan.py
```

## Chạy

```powershell
python scripts/create_prewedding_batch_plan.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút: **Prewedding Batch Plan**.

## Commit

```powershell
git status
git add core/prewedding_batch core/gui/prewedding_batch_plan_patch.py core/gui/__init__.py scripts/create_prewedding_batch_plan.py scripts/test_prewedding_batch_plan.py scripts/build_exe.py README_MODULE_055.md
git commit -m "Add prewedding batch plan"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
