# STT AI Editor - Module 030: Project Workflow Presets

Adds workflow presets for wedding projects.

Presets:

- `Wedding Highlight 60s`
- `Wedding Highlight 3min`
- `Wedding Highlight 5min`
- `Review Culling 30s`

New GUI section:

`Workflow Preset`

Buttons:

- `Apply Preset`
- `Save Preset to Project`
- `Load Project Preset`

Project preset file:

`D:\STT Projects\Wedding_Test_001\stt_workflow_preset.json`

Copy into:

`D:\Projects\STT-AI-Editor`

Run GUI:

```powershell
python scripts/run_gui.py
```

Test CLI:

```powershell
python scripts/test_project_presets.py
```

Run pipeline with preset from CLI:

```powershell
python scripts/run_pipeline_with_preset.py --project "D:\STT Projects\Wedding_Test_001" --preset wedding_highlight_60s
```

Recommended use:

1. Choose `Wedding Highlight 60s`
2. Click `Apply Preset`
3. Click `Save Preset to Project`
4. Click `Run Final Wedding V2 + Live Review`
