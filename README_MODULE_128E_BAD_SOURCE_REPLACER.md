# Module 128E — Bad Source Replacer

Dùng khi chỉ còn một source cụ thể bị sọc chéo dù XML mixed-rate đã đúng.

128E:
- blacklist toàn bộ source lỗi
- tìm source cùng event trước
- ưu tiên khác camera nhưng cùng scene tag / semantic family
- nếu không có cùng event, chọn source cùng nội dung gần nhất
- giữ nguyên vị trí và duration trên timeline
- tự chạy exporter 128D
- khôi phục timeline gốc sau khi export

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

Phải có sẵn:

```text
scripts\export_premiere_mixedrate_repair_128d.py
```

## Chạy cho STT0043.MP4

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/replace_bad_source_and_export_128e.py --project "$PROJECT" --exclude "STT0043.MP4" --preset horizontal_4k --sequence-fps 30 --default-source-fps 50
```

## Import video-only trước

```text
D:\STT Projects\Wedding_Test_001\stt_128e_VIDEO_ONLY_BAD_SOURCE_REPLACED.xml
```

Sau đó:

```text
D:\STT Projects\Wedding_Test_001\stt_128e_SAFE_WITH_MUSIC_BAD_SOURCE_REPLACED.xml
```

Cuối cùng:

```text
D:\STT Projects\Wedding_Test_001\stt_128e_SLOW50_WITH_MUSIC_BAD_SOURCE_REPLACED.xml
```

Có thể blacklist nhiều file:

```powershell
python scripts/replace_bad_source_and_export_128e.py --project "$PROJECT" --exclude "STT0043.MP4" --exclude "STT0099.MP4"
```
