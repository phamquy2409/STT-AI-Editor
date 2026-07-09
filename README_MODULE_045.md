# STT AI Editor - Module 045: AI Style Memory V2

Module này tạo bộ nhớ AI dựng cưới V2.

Nó lấy dữ liệu từ:

- `stt_wedding_style_profile.json` của Module 044
- `manual_selection.json`
- `stt_feedback_profile.json`
- `stt_workflow_preset.json`

Sau đó tạo:

`D:\STT Projects\Wedding_Test_001\stt_ai_style_memory_v2.json`

và copy sang:

`%APPDATA%\STT_AI_Editor\stt_ai_style_memory_v2.json`

## Mục tiêu

Đây là nền để Module 046+ bắt đầu chấm điểm shot theo gu dựng của anh.

Nó lưu:

- gu dựng cưới
- cấu trúc highlight
- shot nào nên ưu tiên
- shot nào nên né
- trọng số chọn shot
- prompt pack cho AI module sau
- intent map: teaser 60s / highlight 3min / highlight 5min / review culling

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_ai_style_memory.py
```

Build memory:

```powershell
python scripts/build_ai_style_memory.py
```

Thêm ghi chú:

```powershell
python scripts/build_ai_style_memory.py --notes "Teaser 60s cần nhanh hơn, nhiều cảm xúc hơn."
```

Chọn intent:

```powershell
python scripts/build_ai_style_memory.py --intent teaser_60s
python scripts/build_ai_style_memory.py --intent highlight_3min
python scripts/build_ai_style_memory.py --intent highlight_5min
python scripts/build_ai_style_memory.py --intent review_culling
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có nút mới:

`Build AI Style Memory V2`

## Sau module này

- 046: AI Shot Scorer V1
- 047: AI Learned Shot Selector
- 048-050: AI học từ KEEP/REJECT/LIKE mạnh hơn
- 055+: AI dựng timeline theo style memory
- 060+: AI nhận lệnh chữ

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/ai_style_memory core/gui/ai_style_memory_patch.py core/gui/__init__.py scripts/build_ai_style_memory.py scripts/test_ai_style_memory.py scripts/build_exe.py README_MODULE_045.md
git commit -m "Add AI style memory v2"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
