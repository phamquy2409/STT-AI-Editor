# Module 091D - Recovery Scan All Clipitems

Fix 091C `clip_count: 0`.

091D:
- Nếu XML bị lỗi, quét toàn bộ `<clipitem>...</clipitem>`
- Dùng file id map để nối `<file id="..."/>` với pathurl thật
- Chỉ bỏ audio/music bằng đuôi file, không phụ thuộc vùng `<video>`

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_finished_project_xml_reader.py

python scripts/create_finished_project_xml_reader.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\27thang6pschh\souce" --final-xml "D:\STT Projects\Wedding_Test_001\final_by_user.xml"
```
