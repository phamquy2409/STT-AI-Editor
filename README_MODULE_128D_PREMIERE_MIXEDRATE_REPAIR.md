# Module 128D — Premiere Mixed-Rate Repair

128C không được dùng nữa.

Lỗi 128C:
- đặt `clipitem rate` bằng FPS source 50fps
- nhưng `start/end` lại là vị trí trong sequence 30fps
- làm Premiere diễn giải sai timeline và tạo thêm rất nhiều sọc chéo

128D sửa theo cấu trúc mixed-rate XMEML:
- sequence: 30fps
- clipitem: 30fps
- clip start/end/in/out: rate của sequence
- file media: FPS thật của source, ví dụ 50fps
- dùng `mixedratesoffset` để bù frame source
- mỗi file source chỉ khai báo đầy đủ một lần
- chừa 5 frame thật ở cuối media

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/export_premiere_mixedrate_repair_128d.py --project "$PROJECT" --preset horizontal_4k --sequence-fps 30 --default-source-fps 50 --max-beat-shift 0.24
```

## Thứ tự kiểm tra bắt buộc

### 1. Video-only, không nhạc, không speed

```text
D:\STT Projects\Wedding_Test_001\stt_128d_VIDEO_ONLY_SAFE.xml
```

Đây là bản dùng để xác nhận sọc source đã hết.

### 2. Video + nhạc, không speed

```text
D:\STT Projects\Wedding_Test_001\stt_128d_SAFE_WITH_MUSIC.xml
```

### 3. Video + nhạc + slow 50%

```text
D:\STT Projects\Wedding_Test_001\stt_128d_SLOW50_WITH_MUSIC.xml
```

Không test bản 2 hoặc 3 trước khi bản video-only hết sọc.
