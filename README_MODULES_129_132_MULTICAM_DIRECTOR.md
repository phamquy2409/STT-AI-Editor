# Modules 129–132 — Multi-Camera Director

Chạy sau 126–128.

## 129 — Camera Source Map

- nhận diện máy theo prefix/folder
- tách DRONE
- đo shot scale sơ bộ: wide / medium / close
- gắn quality + beauty + semantic family

## 130 — Multi-Camera Event Grouper

- gom clip có khả năng cùng một sự kiện
- ưu tiên creation_time nếu có
- fallback bằng tiến trình từng máy + semantic family
- tạo EVENT_001, EVENT_002...

## 131 — Multi-Camera Shot Selector

- giữ lựa chọn Taste AI làm baseline
- chỉ thay góc nếu candidate cùng event tốt hơn rõ rệt
- tránh dùng một máy quá lâu
- ưu tiên wide → medium → close
- không nhét drone giữa ceremony/vow

## 132 — Shot Reservation + Drone Director

- giữ shot tốt cho hook
- giữ shot tốt nhất cho main climax
- giữ couple shot cho ending
- drone chỉ dùng opening / transition / ending
- slow minimum vẫn là 50%
- ghi đè timeline để exporter 128 đọc

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/create_camera_source_map_129.py --project "$PROJECT"

python scripts/create_multicam_event_groups_130.py --project "$PROJECT" --time-gap-sec 90 --fallback-bucket-size 14

python scripts/create_multicam_shot_selector_131.py --project "$PROJECT" --replace-threshold 12

python scripts/create_shot_reservation_drone_director_132.py --project "$PROJECT"

python scripts/export_slow_climax_premiere_xml_128.py --project "$PROJECT" --preset horizontal_4k --fps 30
```

Import:

```text
D:\STT Projects\Wedding_Test_001\stt_climax_slow_premiere_import.xml
```

Bản an toàn:

```text
D:\STT Projects\Wedding_Test_001\stt_climax_directed_SAFE_NO_SPEED.xml
```

## Lưu ý thực tế

Nếu tên file chỉ có 2 prefix như STT và STTA thì 129 sẽ coi đó là 2 camera group.
Nếu camera đồng bộ giờ sai nhiều, 130 sẽ fallback theo tiến trình source chứ không tin tuyệt đối metadata.
