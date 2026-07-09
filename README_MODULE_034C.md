# STT AI Editor - Module 034C: Fix EXE Live Server In-Process

Fix lỗi EXE báo:

`LIVE MANUAL SERVER STARTED`

nhưng browser báo:

`127.0.0.1 refused to connect`

Nguyên nhân:

Trong bản EXE, `sys.executable` không còn là `python.exe`, mà là:

`STT AI Editor.exe`

Nên khi GUI cố chạy:

`STT AI Editor.exe scripts/run_live_manual_review.py`

server có thể chết ngay, browser không kết nối được.

Bản 034C sửa bằng cách:

- Không chạy live server bằng subprocess nữa khi mở từ GUI.
- Chạy `LiveManualReviewServer` trực tiếp bên trong app bằng background thread.
- Nút `Stop Live Server` vẫn tắt được server.
- Không cần file `_internal\scripts\run_live_manual_review.py` nữa, nhưng giữ lại cũng không sao.

Cài:

Copy vào:

`D:\Projects\STT-AI-Editor`

Sau đó build lại EXE:

```powershell
python scripts/build_exe.py
```

Test:

1. Mở:

```text
D:\Projects\STT-AI-Editor\dist\STT AI Editor\STT AI Editor.exe
```

2. Bấm:

`Open Live Manual Review`

3. Browser phải mở:

`http://127.0.0.1:8787`

và hiện trang review.

Commit chung với 034 nếu chưa commit:

```powershell
git status
git add scripts/build_exe.py scripts/build_exe_console.py build_exe.bat build_exe_console.bat README_MODULE_034.md README_MODULE_034B.md README_MODULE_034C.md core/manual_live/live_review_server.py core/gui/exe_live_patch.py core/gui/__init__.py
git commit -m "Add Windows EXE build module with in-process live server fix"
git push
```

Không commit:

`dist/`
`build/`
`*.spec`
