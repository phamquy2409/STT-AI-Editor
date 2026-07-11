# Module 092 - AI vs Final XML Comparator

092 so sánh:
- AI XML ban đầu
- Final XML anh đã sửa trong Premiere
- Folder source gốc

Nó học các khác biệt:
- anh thêm clip nào
- anh bỏ clip nào
- anh giữ clip nào nhưng đổi duration
- anh đổi thứ tự clip ra sao
- section intro/story/build/climax/ending trong final có nhịp ra sao

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_ai_vs_final_xml_comparator.py

python scripts/create_ai_vs_final_xml_comparator.py --project "D:\STT Projects\Wedding_Test_001" --source "D:\27thang6pschh\souce" --ai-xml "D:\STT Projects\Wedding_Test_001\stt_final_wedding_music_cut_premiere_import.xml" --final-xml "D:\STT Projects\Wedding_Test_001\final_by_user.xml"
```

Output chính:
- `stt_ai_vs_final_comparison_v1.json`
- `USER_ADDED_CLIPS.csv`
- `USER_REMOVED_AI_CLIPS.csv`
- `COMMON_CLIP_COMPARISON.csv`
