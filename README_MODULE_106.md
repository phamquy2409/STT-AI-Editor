# STT AI Editor - Module 106: Story Builder V4

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
python scripts/test_story_builder_v4.py
```

## Chạy

```powershell
python scripts/create_story_builder_v4.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent prewedding_reel_60s --target-seconds 60
```

## Commit

```powershell
git add core/story_builder_v4 scripts/create_story_builder_v4.py scripts/test_story_builder_v4.py README_MODULE_106.md
git commit -m "Add story builder v4"
git push
```
