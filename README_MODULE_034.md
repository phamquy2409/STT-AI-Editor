# STT AI Editor - Module 034: Build EXE

Module này thêm script build app thành `.exe`.

Output chính:

`D:\Projects\STT-AI-Editor\dist\STT AI Editor\STT AI Editor.exe`

Cài:

Copy vào:

`D:\Projects\STT-AI-Editor`

Chạy build:

```powershell
python scripts/build_exe.py
```

Hoặc double click:

`build_exe.bat`

Sau khi build xong, mở file:

```text
D:\Projects\STT-AI-Editor\dist\STT AI Editor\STT AI Editor.exe
```

Lưu ý quan trọng:

- Bản này build kiểu `onedir`, không phải `onefile`.
- Nghĩa là phải giữ nguyên cả folder:
  `dist\STT AI Editor\`
- Không được chỉ copy riêng file `.exe`, vì app cần DLL/PySide/OpenCV bên cạnh.
- Bản `onedir` ổn định hơn cho PySide6 + OpenCV.
- Nếu EXE mở nhưng bị tắt ngay, chạy bản console debug:

```powershell
python scripts/build_exe_console.py
```

Output console:

`D:\Projects\STT-AI-Editor\dist\STT AI Editor Console\STT AI Editor Console.exe`

Nếu PyInstaller lỗi với Python 3.14:

Cách xử lý an toàn là tạo venv build bằng Python 3.12 hoặc 3.13, vì PyInstaller có thể chưa ổn định với Python quá mới.

Commit:

```powershell
git status
git add .
git commit -m "Add Windows EXE build module"
git push
```
