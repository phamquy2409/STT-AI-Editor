# STT AI Editor - Module 107: Beat / Climax Cutter

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
python scripts/test_beat_climax_cutter.py
```

## Chạy

```powershell
python scripts/create_beat_climax_cutter.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --target-seconds 60
```

## Commit

```powershell
git add core/beat_climax_cutter scripts/create_beat_climax_cutter.py scripts/test_beat_climax_cutter.py README_MODULE_107.md
git commit -m "Add beat climax cutter"
git push
```
