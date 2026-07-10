# STT AI Editor - Module 102: Pipeline Real Source Timeline Fix

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
python scripts/test_real_source_timeline.py
```

## Chạy

```powershell
python scripts/create_real_source_timeline.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --target-seconds 60
```

## Commit

```powershell
git add core/real_source_timeline scripts/create_real_source_timeline.py scripts/test_real_source_timeline.py README_MODULE_102.md
git commit -m "Fix pipeline real source timeline"
git push
```
