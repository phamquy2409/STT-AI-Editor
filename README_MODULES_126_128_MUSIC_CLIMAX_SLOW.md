# Modules 126–128 — Music Structure, Climax Director, Slow 50%

Gói này chạy sau 123B + 124 + 125.

## 126 — Music Structure + Climax Map

Phân tích:
- intro
- story
- build
- pre-climax
- climax
- release
- ending
- các điểm nhạc mạnh
- cao trào chính

## 127 — Climax Shot Director

- phá nhịp đều 1–2 giây
- intro/story/build/climax/ending có nhịp riêng
- giữ shot tốt cho cao trào
- shot cảm xúc/đẹp được giữ lâu hơn
- chọn lại cửa sổ ổn định theo 124
- không thay toàn bộ source như 125 `--replace-weak`

## 128 — Slow 50% + Premiere XML

- tốc độ chậm nhất đúng 50%
- shot nhấn được tách thành:
  - 100% trước điểm nhấn
  - 50% tại điểm nhấn
  - 100% sau điểm nhấn
- thêm nhạc vào XML
- thêm marker section và emphasis
- tạo thêm XML SAFE không có speed

Lưu ý: V1 dùng 3 segment liền nhau để tạo 100% → 50% → 100%.
Smooth speed-ramp Bezier đầy đủ sẽ làm trong Premiere Extension.

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/create_music_structure_climax_126.py --project "$PROJECT"

python scripts/create_climax_shot_director_127.py --project "$PROJECT" --target-shots 150

python scripts/export_slow_climax_premiere_xml_128.py --project "$PROJECT" --preset horizontal_4k --fps 30
```

Import bản có slow:

```text
D:\STT Projects\Wedding_Test_001\stt_climax_slow_premiere_import.xml
```

Nếu Premiere đọc speed không đúng, import bản an toàn:

```text
D:\STT Projects\Wedding_Test_001\stt_climax_directed_SAFE_NO_SPEED.xml
```
