# STT AI Editor - Module 126: Wedding Story Structure Builder V2

Fix lỗi 122–125 chọn source lộn xộn, chưa ra intro/story/climax rõ.

126 ép timeline theo chương:
- intro_hook
- getting_ready
- gia_tien_story
- ruoc_dau_story
- reception_story
- emotion_climax
- ending_release

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_wedding_story_structure_builder_v2.py
python scripts/create_wedding_story_structure_builder_v2.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --target-seconds 180 --target-shots 76
python scripts/create_emotion_hold_fast_cut_rules.py --project "D:\STT Projects\Wedding_Test_001" --target-seconds 180
python scripts/create_audio_ducking_fade_plan.py --project "D:\STT Projects\Wedding_Test_001" --target-seconds 180
python scripts/export_final_wedding_music_cut_xml.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\5thang5test" --intent wedding_documentary --preset vertical_1080_25p
```
