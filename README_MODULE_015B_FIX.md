# STT AI Editor - Module 015B Fix

Fix lỗi:

`RuntimeError: No KEEP or MAYBE rows found in manual_selection.json`

Nguyên nhân thường là file JSON được export khi chưa bấm KEEP/MAYBE, nên toàn bộ status là `unset`.

Bản 015B sẽ:

- ưu tiên KEEP
- nếu không có KEEP thì lấy MAYBE
- nếu không có MAYBE thì lấy UNSET để test
- luôn bỏ REJECT

Copy file vào repo rồi chạy lại lệnh cũ.
