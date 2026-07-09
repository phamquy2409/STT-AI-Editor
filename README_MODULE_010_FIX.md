# STT AI Editor - Module 010 FIX

This patch fixes:

`AttributeError: module 'cv2' has no attribute 'CascadeClassifier'`

Reason:
Python 3.14 installed OpenCV 5 alpha, which may not include CascadeClassifier.

This fix removes CascadeClassifier and uses:
- skin-color regions
- subject/detail score
- composition score

Run again:

```powershell
python scripts/test_people_composition.py
```
