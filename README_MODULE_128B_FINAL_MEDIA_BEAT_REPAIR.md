# Module 128B — Final Media Boundary + Beat Repair

Bản vá này sửa trực tiếp các lỗi thấy trong Premiere:

- source video bị kéo vượt khỏi duration thật
- phần source/audio xuất hiện sọc chéo
- XML khai báo nhạc dài hơn file thật
- cut bị lệch beat sau khi qua multicam và slow
- slow 50% khi source không đủ frame
- giữ tổng timeline và không tạo gap

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/export_final_media_beat_repair_128b.py --project "$PROJECT" --preset horizontal_4k --fps 30 --max-beat-shift 0.24
```

## Import bản chính

```text
D:\STT Projects\Wedding_Test_001\stt_final_repaired_slow50_premiere_import.xml
```

## Import bản kiểm tra an toàn

```text
D:\STT Projects\Wedding_Test_001\stt_final_repaired_SAFE_NO_SPEED.xml
```

Nên kiểm tra bản SAFE trước. Nếu SAFE không còn source sọc chéo, import tiếp bản slow 50%.

## Kết quả cần chú ý

```text
snapped_cut_count
source_clamped_count
missing_file_count
unknown_duration_count
slow_applied_count
slow_disabled_count
music_duration_sec
music_end_sec
audio_tail_silence_sec
```

- `missing_file_count` nên bằng 0.
- `unknown_duration_count` nên bằng 0.
- `audio_tail_silence_sec` lớn hơn 0 nghĩa là bài nhạc thật ngắn hơn timeline; XML sẽ kết thúc nhạc đúng media thay vì kéo ra sọc chéo.
