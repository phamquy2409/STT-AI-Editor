# STT AI Editor - Module 073: Delivery Checklist

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_delivery_checklist.py
```

## Chạy

```powershell
python scripts/create_delivery_checklist.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Delivery Checklist`

## Commit

```powershell
git status
git add core/delivery_checklist core/gui/delivery_checklist_patch.py core/gui/__init__.py scripts/create_delivery_checklist.py scripts/test_delivery_checklist.py scripts/build_exe.py README_MODULE_073.md
git commit -m "Add delivery checklist"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
