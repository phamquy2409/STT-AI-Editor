# Module 133 — Director Timeline Optimizer

133 tối ưu timeline sau 128F:

- sắp lại shot trong phạm vi nhỏ, không đảo toàn bộ story
- giảm lặp camera liên tục
- giảm lặp cùng source sát nhau
- giữ shot mạnh cho intro / climax / ending
- kéo dài shot cảm xúc
- rút ngắn shot chuyển cảnh
- snap cut về beat lần cuối
- giữ source in/out trong giới hạn
- báo gap / overlap
- sao lưu timeline trước 133

## Cài đặt

Giải nén đè vào:

```text
D:\Projects\STT-AI-Editor
```

## Chạy 133 và tự export luôn

```powershell
$PROJECT="D:\STT Projects\Wedding_Test_001"

python scripts/run_director_timeline_optimizer_133.py --project "$PROJECT" --exclude "STT0043.MP4" --export
```

133 sẽ tự:

1. tối ưu timeline;
2. ghi `stt_director_optimized_timeline_v1.json`;
3. sao lưu timeline cũ;
4. gọi 128E để thay source lỗi;
5. gọi 128F để chèn nhạc.

## XML cuối để import

Bản an toàn:

```text
D:\STT Projects\Wedding_Test_001\stt_128f_SAFE_WITH_MUSIC.xml
```

Bản slow:

```text
D:\STT Projects\Wedding_Test_001\stt_128f_SLOW50_WITH_MUSIC.xml
```

## Chỉ chạy 133, chưa export

```powershell
python scripts/run_director_timeline_optimizer_133.py --project "$PROJECT"
```

Sau đó có thể tự chạy 128E và 128F như trước.

## Khôi phục timeline trước 133

```powershell
Copy-Item "$PROJECT\stt_multicam_directed_before_133_backup.json" "$PROJECT\stt_multicam_directed_timeline_v1.json" -Force
```

## Commit sau khi test Premiere ổn

```powershell
cd D:\Projects\STT-AI-Editor

git add .
git commit -m "Module 133 - Director Timeline Optimizer"
git push origin main

git tag v0.4
git push origin v0.4
```
