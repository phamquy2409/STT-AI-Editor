# STT AI Editor - Module 036: Production GUI Cleanup

Module này dọn giao diện thành kiểu dùng thật:

- Thêm panel trên cùng: `STT Production Workflow`
- Gom workflow chính thành 4 nút:
  1. `Run Final Wedding + Live Review`
  2. `Open Live Manual Review`
  3. `Export Latest Manual XML`
  4. `Open Latest XML Folder`
- Thêm nút:
  - `Health Check`
  - `Stable Backup`
- Thêm checkbox:
  - `Production Mode: ẩn bớt nút cũ / test / legacy`

Các nút cũ không bị xoá. Chỉ bị ẩn khi bật Production Mode. Tắt checkbox là hiện lại.

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test nhanh

```powershell
python scripts/test_production_gui_patch.py
```

Nếu OK, mở GUI:

```powershell
python scripts/run_gui.py
```

Kiểm tra:

- Có panel `STT Production Workflow` trên đầu
- Bấm `Run Final Wedding + Live Review`
- Bấm `Open Live Manual Review`
- Tắt/bật checkbox `Production Mode`

## Build lại EXE

Nếu GUI ổn:

```powershell
python scripts/build_exe.py
```

Mở:

```text
D:\Projects\STT-AI-Editor\dist\STT AI Editor\STT AI Editor.exe
```

## Commit

```powershell
git status
git add core/gui/production_patch.py core/gui/__init__.py scripts/test_production_gui_patch.py scripts/build_exe.py README_MODULE_036.md
git commit -m "Add production GUI cleanup mode"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
