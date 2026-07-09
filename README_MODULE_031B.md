# STT AI Editor - Module 031B: Fix Live Review Thumbnails

Fix lỗi Live Manual Review không hiện ảnh thumbnail.

Nguyên nhân:
Trang đang chạy ở `http://127.0.0.1`, nhưng ảnh/video local trước đó có thể là `file:///...`.
Browser có thể chặn nên khung ảnh bị đen / icon lỗi ảnh.

Bản này sửa bằng cách server tự phục vụ ảnh/video qua:

`/media/<id>`

Copy vào:

`D:\Projects\STT-AI-Editor`

Chạy GUI:

```powershell
python scripts/run_gui.py
```

Test:

1. Nếu server live cũ đang chạy, bấm `Stop Live Server`
2. Bấm lại `Open Live Manual Review`
3. Refresh browser bằng `Ctrl + F5`
4. Thumbnail phải hiện lại

Commit:

```powershell
git status
git add core/manual_live/live_review_server.py README_MODULE_031B.md
git commit -m "Fix live manual review thumbnails"
git push
```
