# STT AI Editor - Module 110: Wedding Source Analyzer V2

110 phân tích source phóng sự cưới kỹ hơn:
- đo duration/fps/resolution
- đo blur/brightness/contrast/motion bằng OpenCV
- phân loại sự kiện cưới tạm thời: getting_ready / details / gia_tien / ruoc_dau / reception / vow_speech / dance_party
- chấm điểm strong_pick / keep / review / reject
- tạo CSV/HTML report để kiểm tra vì sao nó chọn/bỏ source

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_wedding_source_analyzer_v2.py
```

## Chạy nhanh 30 file trước

```powershell
python scripts/create_wedding_source_analyzer_v2.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --max-files 30
```

## Nếu OK, chạy toàn bộ 252 file

```powershell
python scripts/create_wedding_source_analyzer_v2.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --max-files 252
```

## Ghi chú

110 chỉ tạo report phân tích. Module 111 sẽ dùng report này để tạo timeline phóng sự tốt hơn 109.
