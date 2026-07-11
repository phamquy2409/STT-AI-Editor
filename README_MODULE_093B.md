# Module 093B - Multi Style Profile Dataset Learner

Dùng khi anh có nhiều món dựng riêng:

- intro_20_30s
- highlight_1min
- wedding_report_3_4min
- intimate_7_8min
- full_story_intimate_7_12min
- traditional_30_60min
- ruoc_dau_gia_tien_tiec
- ruoc_dau_nha_tho_tiec

## Dataset mẫu

```text
D:\STT Learning Dataset
│
├── intro_20_30s
│   ├── project_01
│   │   ├── final.xml
│   │   └── source
│
├── highlight_1min
│   ├── project_01
│   │   ├── final.xml
│   │   └── source
│
├── intimate_7_8min
│   ├── project_01
│   │   ├── final.xml
│   │   └── source
```

Folder source có thể tên `source` hoặc `souce`.

## Chạy

```powershell
python scripts/test_multi_style_profile_learner.py

python scripts/create_multi_style_profile_learner.py --project "D:\STT Projects\Wedding_Test_001" --dataset "D:\STT Learning Dataset"
```

## Output

```text
D:\STT Projects\Wedding_Test_001\stt_multi_style_profile_memory_v1.json
D:\STT Projects\Wedding_Test_001\stt_style_profiles_v1\intro_20_30s.json
D:\STT Projects\Wedding_Test_001\stt_style_profiles_v1\highlight_1min.json
...
```
