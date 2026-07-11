# STT AI Editor - Module 091: Finished Project XML Reader

091 đọc XML final anh export từ Premiere và nối với folder source gốc.

Nó lấy được:
- file nào anh dùng
- timeline start/end
- source in/out
- duration
- XML pathurl
- source thật có mở được không
- nếu XML mất path thì dò file theo tên trong `--source`

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy test

```powershell
python scripts/test_finished_project_xml_reader.py
```

## Chạy với XML final

Ví dụ anh lưu XML final:

`D:\STT Projects\Wedding_Test_001\final_by_user.xml`

Source gốc:

`D:\27thang6pschh\souce`

Chạy:

```powershell
python scripts/create_finished_project_xml_reader.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\27thang6pschh\souce" --final-xml "D:\STT Projects\Wedding_Test_001\final_by_user.xml"
```

Kết quả:
- `D:\STT Projects\Wedding_Test_001\stt_finished_project_xml_v1.json`
- report HTML/CSV trong `exports\finished_project_xml_reader_091_...`
