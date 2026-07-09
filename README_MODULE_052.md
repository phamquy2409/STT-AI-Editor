# STT AI Editor - Module 052: Prewedding Pipeline Doctor

Module này kiểm tra toàn bộ luồng prewedding 046-051 trước khi build EXE hoặc trước khi import Premiere.

## Nó kiểm tra gì?

- Module 046 / 047 / 048 / 050 / 049 / 051 đã import được chưa
- Script cần thiết có đủ chưa
- Project có file manual / score / selection / roughcut / refined / XML chưa
- Premiere pointer có trỏ đúng XML không
- GUI patch có đủ không
- Đưa lệnh tiếp theo nên chạy

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test import

```powershell
python scripts/test_prewedding_doctor.py
```

## Chạy kiểm tra

```powershell
python scripts/check_prewedding_pipeline.py
```

## Nếu báo ready

Chạy full pipeline:

```powershell
python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s
```

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel:

`Prewedding Pipeline Doctor`

Có nút:

`Check Prewedding Pipeline`

## Build EXE

Sau khi 052 ổn:

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/prewedding_doctor core/gui/prewedding_doctor_patch.py core/gui/__init__.py scripts/check_prewedding_pipeline.py scripts/test_prewedding_doctor.py scripts/build_exe.py README_MODULE_052.md
git commit -m "Add prewedding pipeline doctor"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
