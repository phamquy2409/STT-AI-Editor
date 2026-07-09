# STT AI Editor - Module 058: Review Package

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_review_package.py
```

## Chạy

```powershell
python scripts/create_review_package.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút: **Review Package**.

## Commit

```powershell
git status
git add core/review_package core/gui/review_package_patch.py core/gui/__init__.py scripts/create_review_package.py scripts/test_review_package.py scripts/build_exe.py README_MODULE_058.md
git commit -m "Add review package builder"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
