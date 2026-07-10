# STT AI Editor - Module 105: Smart In-Out Cutter

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
python scripts/test_smart_inout_cutter.py
```

## Chạy

```powershell
python scripts/create_smart_inout_cutter.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --target-seconds 60
```

## Commit

```powershell
git add core/smart_inout_cutter scripts/create_smart_inout_cutter.py scripts/test_smart_inout_cutter.py README_MODULE_105.md
git commit -m "Add smart in out cutter"
git push
```
