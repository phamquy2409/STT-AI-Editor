@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo STT AI Editor - Health Check
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" scripts\health_check.py

echo.
echo Done.
pause
