# Modules 119F + 120D Semantic Sequence Corrector

Bản này không chạy lại GPU. Nó sửa lỗi phân loại bằng ngữ cảnh timeline:

119F:
- decor không được chứa CDCR/stage/game/family nếu top_tags cho thấy có người
- ruoc_dau không được xuất hiện trễ sau vow/game/family
- vow không được xuất hiện ở đoạn tối/game/cuối chương trình
- getting_ready không được xuất hiện ở ending
- tự promote first_look sớm nếu có candidate couple đầu tiên

120D:
- planner strict hơn
- ending không lấy getting_ready / vow / game
- intro không lấy CDCR/family/game
- ceremony không lấy game/party/guest_food
- reception/climax mới dùng wedding_game/party/stage

## Chạy sau khi đã có 119E full

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$PROFILE="single_song_report_3_4min"

python scripts/create_semantic_sequence_corrector_119f.py --project "$PROJECT"

python scripts/create_strict_semantic_story_planner_120d.py --project "$PROJECT" --style-profile "$PROFILE" --target-shots 220

python scripts/export_beat_snapped_beauty_xml_115.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Xem lại contact sheet sau sửa:

```powershell
python scripts/create_scene_review_contact_sheets_121.py --project "$PROJECT" --max-per-tag 80
```

Import:
`D:\STT Projects\Wedding_Test_001\stt_beat_snapped_beauty_premiere_import.xml`
