# STT AI Editor - Module 088: Panel Pipeline Presets

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_panel_pipeline_presets.py
```

## Chạy

```powershell
python scripts/create_panel_pipeline_presets.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Panel Pipeline Presets`

## Commit

```powershell
git status
git add core/panel_pipeline_presets core/gui/panel_pipeline_presets_patch.py core/gui/__init__.py scripts/create_panel_pipeline_presets.py scripts/test_panel_pipeline_presets.py scripts/build_exe.py README_MODULE_088.md
git commit -m "Add panel pipeline presets"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
