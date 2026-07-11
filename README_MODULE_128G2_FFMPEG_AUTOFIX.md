# Module 128G2 — FFmpeg Auto-Fix

Sửa lỗi:

```text
[WinError 2] The system cannot find the file specified
```

Nguyên nhân: Windows không tìm thấy `ffmpeg.exe`.

128G2 tự tìm FFmpeg tại:

- PATH
- biến `FFMPEG_BINARY`
- `D:\Projects\STT-AI-Editor\tools\ffmpeg\bin`
- `.venv`
- package `imageio-ffmpeg`
- thư mục WinGet
- `C:\ffmpeg\bin`

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Cài FFmpeg gọn nhất nếu máy chưa có

```powershell
python -m pip install imageio-ffmpeg
```

## Chạy lại

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/build_stereo_audio_master_128g.py --project "$PROJECT" --music-root "D:\27thang6pschh"
```

## Import

```text
D:\STT Projects\Wedding_Test_001\stt_128g_SAFE_STEREO_MUSIC.xml
```

```text
D:\STT Projects\Wedding_Test_001\stt_128g_SLOW50_STEREO_MUSIC.xml
```
