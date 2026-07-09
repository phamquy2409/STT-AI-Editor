# STT AI Editor - Module 044: Wedding Style Profile

Module này bắt đầu phần "AI học gu dựng" nhưng chưa dựng AI thật.

Nó tạo file:

`D:\STT Projects\Wedding_Test_001\stt_wedding_style_profile.json`

và copy sang:

`%APPDATA%\STT_AI_Editor\stt_wedding_style_profile.json`

Profile lưu các quy tắc dựng cưới:

- cinematic / emotional / modern / not boring
- lễ gia tiên có nhưng không kéo dài tĩnh
- xen gia tiên với reception
- rước dâu có thể xen với reception
- cuối clip có thể là dance party
- ưu tiên bride/groom/vow/reaction
- bỏ rung / out nét / cảnh không nội dung
- chuẩn bị cho AI nhạc/SFX/beat cut sau này

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_wedding_style_profile.py
```

Tạo profile:

```powershell
python scripts/create_wedding_style_profile.py
```

Nếu muốn thêm ghi chú:

```powershell
python scripts/create_wedding_style_profile.py --notes "Dựng teaser 60s nên nhanh hơn, ít lễ hơn."
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có nút mới:

`Create Wedding Style Profile`

## Sau module này

- 045: AI Style Memory V2
- 046-050: AI học shot anh KEEP/REJECT/LIKE kỹ hơn
- 055+: AI dựng timeline theo style profile
- 060+: AI nhận lệnh chữ

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/style_profile core/gui/style_profile_patch.py core/gui/__init__.py scripts/create_wedding_style_profile.py scripts/test_wedding_style_profile.py scripts/build_exe.py README_MODULE_044.md
git commit -m "Add wedding style profile"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
