# Module 128G — Stereo Audio Master

128G sửa:

- nhạc không có sẵn trong sequence
- sequence nhận audio thành hai track mono L/R
- track audio không phải Stereo
- MP3/M4A bị Premiere diễn giải channel mapping không ổn định

Cách làm:

1. chuyển nhạc sang WAV PCM 16-bit;
2. ép đúng 2 channel Stereo;
3. ép sample rate 48 kHz;
4. tạo đúng một track có `premiereTrackType="Stereo"`;
5. chèn WAV vào sequence video đã hết sọc của 128E.

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Chạy tự tìm nhạc

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/build_stereo_audio_master_128g.py --project "$PROJECT" --music-root "D:\27thang6pschh"
```

## Hoặc chỉ định đúng file nhạc

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

$MUSIC=Get-ChildItem "D:\27thang6pschh" -File -Recurse |
Where-Object {
    $_.Name -like "*Enemy Of Truth*" -and
    $_.Extension -match '^\.(mp3|wav|m4a|aac|flac)$'
} |
Select-Object -First 1 -ExpandProperty FullName

python scripts/build_stereo_audio_master_128g.py --project "$PROJECT" --music "$MUSIC"
```

## Import bản SAFE trước

```text
D:\STT Projects\Wedding_Test_001\stt_128g_SAFE_STEREO_MUSIC.xml
```

## Sau đó thử bản slow

```text
D:\STT Projects\Wedding_Test_001\stt_128g_SLOW50_STEREO_MUSIC.xml
```

WAV được tạo tại:

```text
D:\STT Projects\Wedding_Test_001\stt_128g_music_stereo_48k.wav
```

Kết quả đúng cần có:

```text
"ok": true
"generated_count": 2
"stereo_wav_channels": 2
"stereo_wav_sample_rate": 48000
"track_type": "Stereo"
```
