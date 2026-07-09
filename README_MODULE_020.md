# STT AI Editor - Module 020: Direct Manual Save

Goal:
Không cần bấm Export JSON tải về Downloads nữa.

Module này chạy một local server:

`http://127.0.0.1:8787`

Trong browser:

1. Bấm KEEP / REJECT
2. Bấm `Save to Project Folder`
3. Python lưu trực tiếp:
   - `manual_selection.json`
   - `manual_selection_autosave.json`

Run:

```powershell
python scripts/run_live_manual_review.py
```

Sau khi save xong, tắt server bằng `Ctrl+C`, rồi xuất XML:

```powershell
python main.py manual-export --project "D:\STT Projects\Wedding_Test_001" --selection-json "D:\STT Projects\Wedding_Test_001\manual_selection.json"
```

Then import:

`stt_ai_premiere_import.xml`
