@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo STT AI Editor - Stable Backup
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" scripts\create_stable_backup.py

echo.
echo Done.
pause
