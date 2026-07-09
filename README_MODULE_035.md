# STT AI Editor - Module 035: Stable Backup / Health Check

Module chốt bản ổn định đầu tiên.

Thêm 3 việc:

1. Health Check
2. Stable Backup
3. Cleanup build rác

## 1. Health Check

Chạy:

```powershell
python scripts/health_check.py
```

Nó kiểm tra:

- Repo folder
- Project folder
- project.json
- database
- exports
- manual_selection.json
- feedback profile
- xml settings
- EXE folder
- package Python: PySide6 / cv2 / numpy / sqlalchemy
- ffmpeg / git
- XML mới nhất
- manual review mới nhất

Report tạo ở:

`D:\STT Projects\Wedding_Test_001\exports\app_health_...\`

Hoặc double click:

`health_check.bat`

## 2. Stable Backup

Chạy:

```powershell
python scripts/create_stable_backup.py
```

Nó tạo backup zip ở:

`D:\Projects\STT-AI-Editor\releases\STT_AI_Editor_stable_...zip`

Backup gồm:

- source code snapshot
- project settings json
- feedback profile
- xml export settings
- workflow preset
- EXE folder nếu có

Không backup:

- .venv
- .git
- build
- source video cưới
- cache

Hoặc double click:

`create_stable_backup.bat`

## 3. Cleanup build

Chạy:

```powershell
python scripts/cleanup_build_artifacts.py
```

Nó xoá:

- build/
- dist/STT AI Editor Console/
- file .spec

Nó giữ lại:

`dist/STT AI Editor`

## Gitignore

Module có file:

`.gitignore.stt_ai_editor_recommended`

Không tự overwrite `.gitignore` để tránh mất cấu hình cũ.

Nếu git status hiện `dist/`, `build/`, `releases/`, thì copy nội dung file này vào `.gitignore`.

## Commit

```powershell
git status
git add core/app_health scripts/health_check.py scripts/create_stable_backup.py scripts/cleanup_build_artifacts.py health_check.bat create_stable_backup.bat .gitignore.stt_ai_editor_recommended README_MODULE_035.md
git commit -m "Add stable backup and health check module"
git push
```
