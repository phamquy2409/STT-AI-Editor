# STT AI Editor - Module 063: Music Candidate Library

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_music_candidate_library.py
```

## Chạy

```powershell
python scripts/create_music_candidate_library.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút:

`Music Candidate Library`

## Commit

```powershell
git status
git add core/music_library core/gui/music_candidate_library_patch.py core/gui/__init__.py scripts/create_music_candidate_library.py scripts/test_music_candidate_library.py scripts/build_exe.py README_MODULE_063.md
git commit -m "Add music candidate library"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
