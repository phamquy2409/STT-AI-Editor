# Modules 134–136 — Moment, Phrase, Final Cut

Giữ nguyên nền xuất video/audio ổn định của 128H3.

## 134 — Smart Moment Selector V2

- dùng quality windows của 124
- tránh đầu/cuối source
- tránh rung, blur, flash/exposure change
- tùy chọn đọc lại 3 candidate tốt nhất của từng shot
- ưu tiên mức chuyển động phù hợp với loại cảnh
- chọn lại source in/out nhưng không đổi nội dung story

## 135 — Music Phrase & Rhythm Director V2

Không cắt mọi beat giống nhau:

```text
intro       : cách 4–8 beat
story       : cách 2–4 beat
build       : 4 → 2 → 1 beat
pre-climax  : 1–2 beat
climax      : nhanh xen hero hold 4 beat
release     : giãn ra 2–4 beat
ending      : giữ 4–8 beat
```

## 136 — Final Cut Beat Planner V2

- ghép moment 134 vào cut plan 135
- ưu tiên đúng section
- tránh lặp camera/source liên tục
- giữ hero shot ở climax/ending
- source in/out được tính lại theo duration mới
- gap/overlap bằng 0
- ghi đè canonical timeline để 128H3 build XML

---

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Chạy toàn bộ và build luôn 128H

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/run_134_136_pipeline.py --project "$PROJECT" --target-seconds 210 --analyze-action --build-128h --music-root "D:\27thang6pschh"
```

134 chỉ đọc lại các source đang có trên timeline, mỗi source tối đa 3 candidate × 4 frame.
Nó không quét lại toàn bộ 267 source.

## Nếu muốn chạy nhanh, không đọc frame mới

```powershell
python scripts/run_134_136_pipeline.py --project "$PROJECT" --target-seconds 210 --build-128h --music-root "D:\27thang6pschh"
```

## Kết quả cuối

Video-only:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

Nhạc stereo:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```

Import XML, mở panel `STT Audio Bridge`, chọn WAV như bản 128H3.

## Các file trung gian

```text
stt_smart_moment_timeline_v2.json
stt_music_phrase_rhythm_v2.json
stt_final_cut_beat_timeline_v2.json
```

## Khôi phục timeline trước 136

```powershell
Copy-Item "$PROJECT\stt_multicam_directed_before_136_backup.json" "$PROJECT\stt_multicam_directed_timeline_v1.json" -Force
```
