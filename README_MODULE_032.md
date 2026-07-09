# STT AI Editor - Module 032: Feedback Learning from KEEP / REJECT

Module này cho app học từ lựa chọn thủ công của anh.

Nguồn học:

`D:\STT Projects\Wedding_Test_001\manual_selection.json`

Tín hiệu học:

- KEEP = tăng điểm loại shot tương tự
- MAYBE = tăng nhẹ
- REJECT = trừ điểm loại shot tương tự
- Like = cộng thêm

Profile học được lưu tại:

`D:\STT Projects\Wedding_Test_001\stt_feedback_profile.json`

Output test:

`D:\STT Projects\Wedding_Test_001\exports\feedback_learning_...`

`D:\STT Projects\Wedding_Test_001\exports\learned_candidates_...`

Copy vào:

`D:\Projects\STT-AI-Editor`

Test học + apply score:

```powershell
python scripts/test_feedback_learning.py
```

Test full learned pipeline + XML:

```powershell
python scripts/run_learned_pipeline.py
```

Output XML nằm trong folder `learned_candidates_...` hoặc folder XML mới nhất.

Workflow:

1. Run Final Wedding V2 + Live Review
2. KEEP / REJECT / Like
3. Save to Project Folder
4. Chạy:
   `python scripts/run_learned_pipeline.py`
5. Import XML mới vào Premiere xem app đã học gu chọn shot chưa

Commit:

```powershell
git status
git add .
git commit -m "Add feedback learning module"
git push
```
