# STT AI Editor - Module 049: Prewedding XML Exporter

Module này xuất XML Premiere từ selection của Module 047.

## Input

`D:\STT Projects\Wedding_Test_001\stt_prewedding_selection_v1.json`

## Output

Trong `exports\prewedding_xml_...` có:

- `stt_prewedding_premiere_import.xml`
- `README_IMPORT_PREMIERE.txt`
- `PREWEDDING_XML_IMPORT_STEPS.html`
- `premiere_import_prewedding_xml.jsx`
- `Copy_XML_Path_To_Clipboard.bat`
- `prewedding_xml_manifest.json`

Đồng thời copy XML mới nhất vào:

`D:\STT Projects\Wedding_Test_001\stt_prewedding_premiere_import.xml`

và update Premiere pointer:

`%APPDATA%\STT_AI_Editor\premiere_latest_xml.txt`

## Preset

- `vertical_1080_25p`
- `vertical_1080_30p`
- `fhd_1080_25p`
- `uhd_4k_25p`

Nếu để auto:

- reel → `vertical_1080_25p`
- cinematic/location → `fhd_1080_25p`

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_prewedding_xml.py
```

## Export XML auto preset

```powershell
python scripts/export_prewedding_xml.py
```

## Export XML reel dọc 9:16

```powershell
python scripts/export_prewedding_xml.py --preset vertical_1080_25p
```

## Export XML ngang 1080p

```powershell
python scripts/export_prewedding_xml.py --preset fhd_1080_25p
```

## Workflow đúng

```powershell
python scripts/run_ai_shot_scorer.py --intent prewedding_reel_60s
python scripts/build_prewedding_selection.py --intent prewedding_reel_60s
python scripts/export_prewedding_xml.py --preset vertical_1080_25p
```

Sau đó vào Premiere:

- Cách 1: File > Import > chọn XML
- Cách 2: Window > Extensions > STT AI Editor > Refresh Latest XML > Import Latest XML

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel:

`Prewedding XML Export`

Có preset dropdown và nút:

`Export Prewedding XML`

## Audio

Giữ kiểu an toàn:

`A1 = Left, A2 = Right`

Không dùng fix stereo cũ làm mất kênh phải.

## Build EXE

```powershell
python scripts/build_exe.py
```

## Commit

```powershell
git status
git add core/prewedding_xml core/gui/prewedding_xml_patch.py core/gui/__init__.py scripts/export_prewedding_xml.py scripts/test_prewedding_xml.py scripts/build_exe.py README_MODULE_049.md
git commit -m "Add prewedding Premiere XML exporter"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
