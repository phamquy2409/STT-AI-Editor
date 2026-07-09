# STT AI Editor - Module 033: XML Export Options / Sequence Presets

Module này thêm preset xuất XML cho Premiere.

Preset có sẵn:

- `uhd_4k_25p` = UHD 4K 25p, 3840x2160
- `uhd_4k_50p` = UHD 4K 50p, 3840x2160
- `fhd_1080_25p` = Full HD 1080p 25p
- `dci_4k_24p` = DCI 4K 24p, 4096x2160
- `vertical_1080_25p` = Dọc 1080x1920 25p

Settings lưu tại:

`D:\STT Projects\Wedding_Test_001\stt_xml_export_settings.json`

Copy vào:

`D:\Projects\STT-AI-Editor`

Test:

```powershell
python scripts/test_xml_export_options.py
```

Xuất XML từ roughcut mới nhất với preset 4K 25p:

```powershell
python scripts/export_xml_with_options.py --preset uhd_4k_25p
```

Xuất XML dọc 1080x1920:

```powershell
python scripts/export_xml_with_options.py --preset vertical_1080_25p
```

Xuất XML từ file JSON cụ thể:

```powershell
python scripts/export_xml_with_options.py --roughcut-json "D:\STT Projects\Wedding_Test_001\exports\learned_candidates_xxx\roughcut_learned_candidates.json" --preset uhd_4k_25p
```

Lưu ý:

- Bản này không thay exporter gốc.
- Nó chỉ bọc exporter gốc bằng sequence preset.
- Audio vẫn giữ kiểu an toàn cũ để không mất kênh R.

Commit:

```powershell
git status
git add .
git commit -m "Add XML export options module"
git push
```
