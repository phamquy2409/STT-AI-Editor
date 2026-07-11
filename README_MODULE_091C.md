# Module 091C - XML File ID Resolver

Fix tiếp cho 091B:
- XML bị lỗi vẫn đọc recovery
- đọc file id map: `<file id="...">`
- clipitem chỉ có `<file id="..."/>` vẫn nối được pathurl
- mặc định chỉ lấy video clip, bỏ audio/music để học source hình

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_finished_project_xml_reader.py

python scripts/create_finished_project_xml_reader.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\27thang6pschh\souce" --final-xml "D:\STT Projects\Wedding_Test_001\final_by_user.xml"
```

Nếu muốn đọc cả audio:

```powershell
python scripts/create_finished_project_xml_reader.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\27thang6pschh\souce" --final-xml "D:\STT Projects\Wedding_Test_001\final_by_user.xml" --include-audio
```
