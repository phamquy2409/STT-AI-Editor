# STT AI Editor - Module 065: Audio Cue Planner

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_audio_cue_planner.py
```

## Chạy

```powershell
python scripts/create_audio_cue_planner.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Audio Cue Planner`

## Commit

```powershell
git status
git add core/audio_cue_planner core/gui/audio_cue_planner_patch.py core/gui/__init__.py scripts/create_audio_cue_planner.py scripts/test_audio_cue_planner.py scripts/build_exe.py README_MODULE_065.md
git commit -m "Add audio cue planner"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
