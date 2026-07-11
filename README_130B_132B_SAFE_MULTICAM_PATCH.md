# 130B–132B Safe Multi-Camera Patch

Sửa các lỗi thấy từ lần chạy đầu:

- 129 có 267 `shot_scale=unknown`: không dùng shot scale để quyết định thay góc.
- 130 cũ có `multi_camera_event_count=0`: đổi sang gom theo tiến trình tương đối của từng camera.
- 131 cũ thay 80/106 shot: bản mới chỉ thay:
  - cùng event
  - khác camera
  - cùng tag hoặc cùng semantic family
  - tốt hơn rõ ràng
  - tối đa 25% timeline
- 132 cũ có thể đổi thứ tự shot giữa các section: bản mới chỉ đánh dấu shot tốt nhất trong chính hook/climax/ending, không đảo story.

## Khôi phục timeline 126–128 trước

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/create_climax_shot_director_127.py --project "$PROJECT" --target-shots 150
```

## Chạy bản vá

```powershell
python scripts/create_multicam_event_groups_130b.py --project "$PROJECT"

python scripts/create_multicam_shot_selector_131b.py --project "$PROJECT" --replace-threshold 18 --max-replace-ratio 0.25

python scripts/create_safe_shot_reservation_132b.py --project "$PROJECT"

python scripts/export_slow_climax_premiere_xml_128.py --project "$PROJECT" --preset horizontal_4k --fps 30
```

Kết quả tốt nên có:

- `multi_camera_event_count` gần bằng `event_count`
- `replaced_count` từ 0 đến khoảng 26 với timeline 106 shot
- `story_reordered: false`
