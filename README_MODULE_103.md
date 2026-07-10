# STT AI Editor - Module 103: Bad Shot Killer V2

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
python scripts/test_bad_shot_killer_v2.py
```

## Chạy

```powershell
python scripts/create_bad_shot_killer_v2.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --target-seconds 60
```

## Commit

```powershell
git add core/bad_shot_killer_v2 scripts/create_bad_shot_killer_v2.py scripts/test_bad_shot_killer_v2.py README_MODULE_103.md
git commit -m "Add bad shot killer v2"
git push
```
