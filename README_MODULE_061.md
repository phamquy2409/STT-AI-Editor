# STT AI Editor - Module 061: Project Command Center

Module này tạo một folder trung tâm chứa các file `.bat` để chạy nhanh workflow.

## Có gì?

- Check Prewedding Pipeline
- Run Full Prewedding Reel 60s
- Run Full Prewedding Reel 30s
- Run Full Prewedding Cinematic
- Create Master Dashboard
- Create Review Package
- Create Premiere Relink Report
- Create Music Beat Plan
- Create Pipeline Snapshot
- Build EXE
- Package Release
- Open Project / Exports / Repo / Releases

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_project_command_center.py
```

## Chạy

```powershell
python scripts/create_project_command_center.py
```

Output nằm trong:

```text
D:\STT Projects\Wedding_Test_001\exports\project_command_center_YYYYMMDD_HHMMSS
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel:

`Project Command Center`

## Commit

```powershell
git status
git add core/project_command_center core/gui/project_command_center_patch.py core/gui/__init__.py scripts/create_project_command_center.py scripts/test_project_command_center.py scripts/build_exe.py README_MODULE_061.md
git commit -m "Add project command center"
git push
```

Không commit:

```text
dist/
build/
releases/
*.spec
```
