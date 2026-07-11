# Module 128H — Premiere Audio Bridge

128H xử lý hai lỗi còn lại:

- blacklist `STT0043.MP4`
- blacklist `STT0008.MP4`
- không đưa audio qua FCP7 XML nữa
- tạo WAV Stereo PCM 48 kHz
- panel Premiere tự import WAV và đặt vào một audio track mới

## 1. Cài module

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## 2. Build XML video-only + WAV stereo

```powershell
cd D:\Projects\STT-AI-Editor

$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/build_premiere_audio_bridge_128h.py --project "$PROJECT" --music-root "D:\27thang6pschh"
```

Kết quả:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```

## 3. Cài panel Premiere

Chạy trong PowerShell tại project:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_128h_extension.ps1
```

Đóng hẳn Premiere rồi mở lại.

## 4. Dùng trong Premiere

1. Import:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_VIDEO_ONLY_FINAL.xml
```

2. Mở sequence vừa import.
3. Mở:

```text
Window > Extensions (Legacy) > STT Audio Bridge
```

4. Bấm:

```text
Import + đặt nhạc Stereo
```

5. Chọn:

```text
D:\STT Projects\Wedding_Test_001\stt_128h_music_STEREO_48K.wav
```

Panel sẽ tạo audio track mới rồi đặt WAV ở 00:00:00:00.

## Vì sao không dùng audio XML nữa?

Premiere/FCP7 XML có thể nhập stereo thành hai component L/R.
128H dùng Premiere scripting để import media và đặt clip trực tiếp vào active sequence.
