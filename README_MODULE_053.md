# STT AI Editor - Module 053: Release Packager

Module này tạo bản đóng gói app sau khi build EXE.

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test import

```powershell
python scripts/test_release_packager.py
```

## Cách dùng chuẩn

Nếu chưa build EXE:

```powershell
python scripts/build_exe.py
python scripts/package_release.py
```

Hoặc build + package một lệnh:

```powershell
python scripts/package_release.py --build-first
```

## Output

Tạo folder:

```text
releases\STT_AI_Editor_v0.53_YYYYMMDD_HHMMSS
```

Bên trong có:

- Folder app `STT AI Editor`
- `README_INSTALL.txt`
- `Run_STT_AI_Editor.bat`
- `Open_App_Folder.bat`
- `release_manifest.json`
- `RELEASE_SUMMARY.html`

Đồng thời tạo ZIP:

```text
releases\STT_AI_Editor_v0.53_YYYYMMDD_HHMMSS.zip
```

## Lưu ý

Khi đem qua máy khác, copy nguyên folder:

```text
STT AI Editor
```

Không copy riêng file `.exe`, vì EXE cần folder `_internal`.

## GUI

Mở:

```powershell
python scripts/run_gui.py
```

Có panel:

```text
App Release Packager
```

Có nút:

```text
Create Release Package
```

Có tick:

```text
Build EXE first
```

## Commit

```powershell
git status
git add core/release_packager core/gui/release_packager_patch.py core/gui/__init__.py scripts/package_release.py scripts/test_release_packager.py scripts/build_exe.py README_MODULE_053.md
git commit -m "Add release packager"
git push
```

Không commit:

- `dist/`
- `build/`
- `releases/`
- `*.spec`
