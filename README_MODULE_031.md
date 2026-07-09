# STT AI Editor - Module 031: Modern Manual Review UI

Cải thiện trang chọn shot thủ công.

Tính năng mới:

- Card lớn hơn, dễ nhìn hơn
- KEEP / MAYBE / REJECT rõ hơn
- Nút Like
- Ô Note
- Filter theo scene
- Filter theo status
- Search theo tên file / scene
- Phím tắt:
  - `K` = KEEP
  - `M` = MAYBE
  - `R` = REJECT
  - `Space` / Arrow Right = shot kế tiếp
  - Arrow Left = shot trước
- Live Review cũng dùng UI mới
- Live Review vẫn lưu trực tiếp vào:
  `D:\STT Projects\Wedding_Test_001\manual_selection.json`

Copy vào:

`D:\Projects\STT-AI-Editor`

Chạy GUI:

```powershell
python scripts/run_gui.py
```

Test khuyến nghị:

1. Bấm `Run Final Wedding V2 + Live Review`
2. Browser mở trang Live Manual Review mới
3. Dùng K/M/R để chọn shot
4. Bấm `Save to Project Folder`
5. Về GUI bấm `Export Latest Manual XML`

Test manual review cũ:

```powershell
python scripts/test_manual_review_ui.py
```

Test live review riêng:

```powershell
python scripts/run_live_manual_review.py
```
