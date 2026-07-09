# STT AI Editor - Module 013B: Strong Diversity Story Timeline

This patch replaces Module 013 logic.

Why:
Module 013 looked too similar because it still picked mostly the same highest-scoring shots.

Fix:
- max 1 segment per source video by default
- alternates detail / people / motion / people
- intentionally pulls from top + middle candidate bands
- stronger penalty for repeating same source
- creates visibly more varied timeline

Run:

```powershell
python scripts/test_story_timeline.py
```
