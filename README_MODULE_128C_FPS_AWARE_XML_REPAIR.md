# Module 128C — FPS-Aware XML Repair

Bản này sửa lỗi clip bị sọc chéo trong Premiere do:

- sequence là 30fps
- source thực tế là 50fps
- XML cũ dùng 30fps cho cả source
- Premiere hiểu duration source chỉ còn khoảng 60%, nên phần đuôi clip bị thiếu media

128C tách riêng:

- timeline/sequence: 30fps
- từng source: đọc FPS thật bằng ffprobe, ví dụ 50fps
- source in/out: tính theo frame rate thật của source
- file duration: tính theo FPS thật của source
- giữ lại 3 frame an toàn ở cuối source
- nhạc không bị khai báo dài hơn file thật
- snap beat lần cuối
- slow 50% chỉ khi source còn đủ frame

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/export_fps_aware_xml_repair_128c.py --project "$PROJECT" --preset horizontal_4k --sequence-fps 30 --default-source-fps 50 --max-beat-shift 0.24
```

## Import bản SAFE trước

```text
D:\STT Projects\Wedding_Test_001\stt_final_fps_aware_SAFE_NO_SPEED.xml
```

## Sau khi SAFE hết sọc chéo

```text
D:\STT Projects\Wedding_Test_001\stt_final_fps_aware_slow50.xml
```

Kết quả mong muốn:

```text
source_fps_counts: 50fps hoặc FPS thật của từng file
mixed_fps_clip_count: gần bằng timeline_count
missing_file_count: 0
unknown_duration_count: 0
```
