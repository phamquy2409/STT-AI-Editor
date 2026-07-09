# STT AI Editor - Module 031C: Generate Missing Live Thumbnails

Fix tiếp lỗi Live Manual Review vẫn đen thumbnail.

Bản 031B chỉ serve thumbnail nếu thumbnail cũ tồn tại.
Bản 031C sẽ tự tạo thumbnail mới từ source video nếu không tìm thấy ảnh cũ.

Thumbnail mới lưu vào:

`<folder json đang review>\_live_thumbnails\`

Copy vào:

`D:\Projects\STT-AI-Editor`

Cách test:

1. Trong GUI bấm `Stop Live Server`
2. Đóng tab `127.0.0.1:8787` cũ
3. Copy module này vào repo, Replace
4. Chạy lại GUI:

```powershell
python scripts/run_gui.py
```

5. Bấm `Open Live Manual Review`
6. Nếu trình duyệt vẫn giữ cache, bấm `Ctrl + F5`

Trong terminal/log sẽ thấy dòng kiểu:

`generated thumbnail: ...\_live_thumbnails\live_thumb_0001.jpg`

Commit:

```powershell
git status
git add core/manual_live/live_review_server.py README_MODULE_031C.md
git commit -m "Generate missing live review thumbnails"
git push
```
