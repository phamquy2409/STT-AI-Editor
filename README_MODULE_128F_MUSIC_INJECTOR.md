# Module 128F — Music Injector

Giữ nguyên phần video của 128E đã hết sọc, sau đó chèn lại nhạc bằng audio track XMEML riêng.

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Tìm đúng đường dẫn file nhạc

```powershell
Get-ChildItem "D:\27thang6pschh" -File -Recurse |
Where-Object { $_.Extension -match '^\.(mp3|wav|m4a|aac|flac)$' } |
Select-Object FullName
```

Copy đúng `FullName`, sau đó chạy:

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"
$MUSIC="D:\27thang6pschh\DUONG-DAN-CHINH-XAC\Enemy Of Truth.mp3"

python scripts/inject_music_into_fixed_xml_128f.py --project "$PROJECT" --music "$MUSIC"
```

## Import bản an toàn

```text
D:\STT Projects\Wedding_Test_001\stt_128f_SAFE_WITH_MUSIC.xml
```

## Import bản slow

```text
D:\STT Projects\Wedding_Test_001\stt_128f_SLOW50_WITH_MUSIC.xml
```
