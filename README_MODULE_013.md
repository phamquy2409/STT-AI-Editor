# STT AI Editor - Module 013: Story Timeline Structure

Copy files into:

`D:\Projects\STT-AI-Editor`

Run:

```powershell
python scripts/test_story_timeline.py
```

What it does:

- reads latest expanded candidate scoring file
- builds a more wedding-like timeline structure:
  - opening
  - intro_people
  - detail_break
  - main_people
  - closing
- avoids too many clips from the same source
- alternates detail / people / motion roles
- exports:
  - roughcut_story.json
  - roughcut_story.csv
  - roughcut_plan.json
  - stt_ai_premiere_import.xml
  - review.html

Then import:

`D:\STT Projects\Wedding_Test_001\exports\story_timeline_...\stt_ai_premiere_import.xml`
