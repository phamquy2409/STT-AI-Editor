# STT AI Editor - Module 059: Workflow Templates

## Cài

Copy vào:

`D:\Projects\STT-AI-Editor`

Chọn Replace.

## Test

```powershell
python scripts/test_workflow_templates.py
```

## Chạy

```powershell
python scripts/create_workflow_templates.py
```

## GUI

```powershell
python scripts/run_gui.py
```

Sẽ có panel/nút: **Workflow Templates**.

## Commit

```powershell
git status
git add core/workflow_templates core/gui/workflow_templates_patch.py core/gui/__init__.py scripts/create_workflow_templates.py scripts/test_workflow_templates.py scripts/build_exe.py README_MODULE_059.md
git commit -m "Add workflow templates"
git push
```

Không commit `dist/`, `build/`, `releases/`, `*.spec`.
