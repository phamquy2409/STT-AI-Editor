# STT AI Editor - Module 066: Final Replace Checker

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_final_replace_checker.py
```

## Chạy

```powershell
python scripts/create_final_replace_checker.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Final Replace Checker`

## Commit

```powershell
git status
git add core/final_replace_checker core/gui/final_replace_checker_patch.py core/gui/__init__.py scripts/create_final_replace_checker.py scripts/test_final_replace_checker.py scripts/build_exe.py README_MODULE_066.md
git commit -m "Add final replacement checker"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
