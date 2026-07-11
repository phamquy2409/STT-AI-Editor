# Module 093 - Editing Style Memory Builder

093 đọc output 091/092 và tạo style memory:

`stt_user_editing_style_memory_v1.json`

Nó học:
- số clip trong bản final
- độ dài trung bình clip
- tỉ lệ intro/story/build/climax/ending
- clip anh thêm
- clip AI chọn nhưng anh bỏ
- duration/ordering anh sửa

## Cài

Copy đè vào:

`D:\Projects\STT-AI-Editor`

## Chạy

```powershell
python scripts/test_editing_style_memory_builder.py

python scripts/create_editing_style_memory_builder.py --project "D:\STT Projects\Wedding_Test_001" --profile-name "stt_wedding_documentary"
```
