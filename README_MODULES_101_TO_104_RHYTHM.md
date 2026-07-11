# Modules 101-104 Rhythm Intelligence

Fix nhịp dựng đều đều:
- 101 đọc beat/energy thật từ nhạc bằng ffmpeg
- 102 tạo map voice/pause từ clip voice-like/vow/speech/lễ
- 103 tạo nhịp ngắn-dài theo beat và giữ dài khi voice
- 104 export XML gapless video-only theo nhịp mới

## Chạy

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$PROFILE="intimate_7_8min"
$MUSIC_FOLDER="D:\27thang6pschh"

python scripts/create_music_beat_map_101.py --project "$PROJECT" --music-folder "$MUSIC_FOLDER" --target-seconds 480

python scripts/create_voice_pause_map_102.py --project "$PROJECT"

python scripts/create_beat_voice_rhythm_timeline_103.py --project "$PROJECT" --style-profile "$PROFILE" --target-seconds 480 --target-shots 180

python scripts/export_beat_voice_gapless_xml_104.py --project "$PROJECT" --style-profile "$PROFILE" --preset horizontal_4k --fps 30
```

Import XML:

```text
D:\STT Projects\Wedding_Test_001\stt_beat_voice_gapless_premiere_import.xml
```

Bản này chưa nhúng nhạc để tránh lỗi audio XML. Kéo nhạc vào Premiere thủ công trước; sau khi video rhythm OK mới làm audio-safe exporter.
