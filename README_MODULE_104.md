# STT AI Editor - Module 104: Shake / Blur Detector

## Mục tiêu

Module này thuộc nhóm sửa pipeline thật sau 101E:
- giữ source path thật
- không còn source giả `prewedding_clip_1`
- tạo in/out/duration khác nhau
- chuẩn bị XML 101E import vào Premiere online được

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Test

```powershell
python scripts/test_shake_blur_detector.py
```

## Chạy

```powershell
python scripts/create_shake_blur_detector.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --target-seconds 60
```

## Commit

```powershell
git add core/shake_blur_detector scripts/create_shake_blur_detector.py scripts/test_shake_blur_detector.py README_MODULE_104.md
git commit -m "Add shake blur detector"
git push
```
