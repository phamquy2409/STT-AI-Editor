# STT AI Editor - Module 111: Smart Wedding Timeline Selector

111 dùng report từ 110 để dựng timeline sạch hơn 109.

Sửa các lỗi:
- source rung/lắc
- source out-focus / quá tối / quá sáng
- source lặp gần nhau
- source không ý nghĩa nhưng bị lấy vì nằm đúng thứ tự sự kiện

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_smart_wedding_timeline_selector.py
```

## Chạy sau khi 110 đã xong

Phóng sự cưới test 3 phút:

```powershell
python scripts/create_smart_wedding_timeline_selector.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --target-seconds 180
```

Nếu muốn gắt hơn, bỏ source `review`:

```powershell
python scripts/create_smart_wedding_timeline_selector.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --target-seconds 180 --no-review
```

Sau đó export XML bằng 101E:

```powershell
python scripts/export_premiere_safe_fcp7_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --preset vertical_1080_25p --fallback-clip-count 40
```

Mục tiêu:
- `fallback_from_source_folder: false`
- `timeline_items` nhiều hơn 3
- source ít rung/lặp hơn 109
