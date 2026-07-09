# STT AI Editor - Module 016: One Click Pipeline

Copy files into:

`D:\Projects\STT-AI-Editor`

Run existing project pipeline:

```powershell
python scripts/test_one_click_pipeline.py
```

This skips scan/detect/analyze because your current test project already has them done.

Manual CLI:

```powershell
python main.py pipeline --project "D:\STT Projects\Wedding_Test_001" --source-folder "D:\5thang5test" --target-duration 60 --top-candidates 120
```

For a new project that has not been scanned/analyzed yet:

```powershell
python main.py pipeline --project "D:\STT Projects\Wedding_Test_001" --source-folder "D:\5thang5test" --from-scratch --target-duration 60 --top-candidates 120
```

Pipeline steps:

- scan, detect, analyze: optional
- report
- expand candidates
- best moments
- people/composition
- story timeline
- Premiere XML
- review HTML
- manual review HTML

Output:

`D:\STT Projects\Wedding_Test_001\exports\pipeline_run_YYYYMMDD_HHMMSS`

Inside:

- `pipeline_log.txt`
- `pipeline_result.json`

Final XML is also printed in Terminal.
