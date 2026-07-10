# STT AI Editor - Module 109: Wedding Documentary Intent Router

Dùng cho source phóng sự cưới, không dùng logic prewedding reel.

## Intent hỗ trợ

- `wedding_documentary`
- `wedding_highlight_3min`
- `wedding_teaser_60s`
- `gia_tien_story`
- `reception_story`

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_wedding_documentary_intent.py
```

## Chạy với source 5thang5test

Phóng sự cưới test 3 phút:

```powershell
python scripts/create_wedding_documentary_intent.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --target-seconds 180
```

Hoặc teaser cưới 60s:

```powershell
python scripts/create_wedding_documentary_intent.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_teaser_60s --target-seconds 60
```

Sau đó export XML bằng 101E:

```powershell
python scripts/export_premiere_safe_fcp7_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --preset vertical_1080_25p --fallback-clip-count 40
```

Nếu exporter không nhận intent mới, dùng lại:

```powershell
python scripts/export_premiere_safe_fcp7_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --preset vertical_1080_25p --fallback-clip-count 40
```

Exporter vẫn đọc `stt_prewedding_refined_v1.json` do 109 vừa ghi.
