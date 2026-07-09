# STT AI Editor - Module 002: Media Scanner

Copy files into `D:\Projects\STT-AI-Editor`.

Run:

```powershell
python scripts/test_media_scanner.py
```

This scans the source folder stored in:

`D:\STT Projects\Wedding_Test_001\project.json`

If the source path does not exist, edit this file:

`scripts/test_media_scanner.py`

Change:

```python
source_folder = None
```

to your real video folder, example:

```python
source_folder = Path("D:/Wedding/Source")
```

Then run again.
