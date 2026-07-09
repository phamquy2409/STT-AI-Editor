# STT AI Editor - Module 062: Music Placeholder Manager

Module này quản lý nhạc tạm / preview / watermark và tạo cue sheet để final thay đúng bài.

## Nó làm gì?

- Tạo folder:
  - `music/music_previews`
  - `music/music_final`
  - `music/cue_sheets`
- Tạo:
  - `MUSIC_CUE_SHEET.csv`
  - `MUSIC_LICENSE_LINKS.html`
  - `MUSIC_REPLACE_GUIDE.txt`
  - `MUSIC_SEARCH_PROMPT.txt`
  - `music_candidates_template.csv`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_music_placeholder_manager.py
```

## Chạy mặc định

```powershell
python scripts/create_music_placeholder_manager.py --intent prewedding_reel_60s
```

## Dùng CSV bài đã chọn

Điền bài vào file template:

```text
music_candidates_template.csv
```

Sau đó chạy:

```powershell
python scripts/create_music_placeholder_manager.py --intent prewedding_reel_60s --candidates "D:\path\music_candidates_template.csv"
```

## Copy preview hợp lệ vào project

```powershell
python scripts/create_music_placeholder_manager.py --intent prewedding_reel_60s --preview-file "D:\Downloads\song_preview.mp3"
```

## GUI

```powershell
python scripts/run_gui.py
```

Có panel:

`Music Placeholder / Cue Sheet`

## Lưu ý bản quyền

Không tự tải lậu từ YouTube video thường. Chỉ dùng:

- preview/watermark hợp lệ từ Artlist/Musicbed nếu platform cho phép
- YouTube Audio Library
- file anh đã có license
- file anh tự tải thủ công hợp lệ

## Commit

```powershell
git status
git add core/music_placeholder core/gui/music_placeholder_patch.py core/gui/__init__.py scripts/create_music_placeholder_manager.py scripts/test_music_placeholder_manager.py scripts/build_exe.py README_MODULE_062.md
git commit -m "Add music placeholder cue sheet manager"
git push
```

Không commit:

```text
dist/
build/
releases/
*.spec
```
