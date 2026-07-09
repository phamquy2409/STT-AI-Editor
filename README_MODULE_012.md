# STT AI Editor - Module 012: Full Source Candidate Expansion

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_full_candidate_expansion.py
```

What it does:

- goes back to the whole database, not only the old 23-shot roughcut
- scans all analyzed shot_segments, usually 1357 segments
- ranks the best 120 candidates
- runs Best Moment Finder again
- runs People / Composition scoring again
- builds new final roughcut
- exports Premiere XML
- opens final review.html

Output folders:

- `expanded_candidates_YYYYMMDD_HHMMSS`
- `final_roughcut_YYYYMMDD_HHMMSS`

Manual command for only expansion:

```powershell
python main.py expand-candidates --project "D:\STT Projects\Wedding_Test_001" --top-candidates 120 --min-ai-score 30 --max-segments-per-video 6
```

After test, import this XML in Premiere:

`D:\STT Projects\Wedding_Test_001\exports\final_roughcut_...\stt_ai_premiere_import.xml`
