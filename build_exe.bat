@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo STT AI Editor - Build EXE
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found.
    echo Run this from D:\Projects\STT-AI-Editor
    pause
    exit /b 1
)

".venv\Scripts\python.exe" scripts\build_exe.py

echo.
echo Done.
pause
