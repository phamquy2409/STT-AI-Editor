# Module 091B - Finished XML Recovery Reader

Fix lỗi:

`xml.etree.ElementTree.ParseError: unclosed token`

091B:
- parse XML chuẩn nếu file OK
- nếu XML bị lỗi/truncated, tự chuyển qua recovery mode
- quét từng `<clipitem>...</clipitem>` để vẫn đọc timeline/source

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_finished_project_xml_reader.py

python scripts/create_finished_project_xml_reader.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\27thang6pschh\souce" --final-xml "D:\STT Projects\Wedding_Test_001\final_by_user.xml"
```

Nếu kết quả có:

`parse_mode: recovery_clipitem_scan`

nghĩa là file XML final có lỗi format nhưng tool vẫn đọc cứu hộ được.
