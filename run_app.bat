@echo off
setlocal enabledelayedexpansion

title Live Spreadsheet - Local App

echo ======================================================================
echo                 LIVE SPREADSHEET - 1-CLICK LAUNCHER
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Detect Python executable
set "PY_CMD="
if exist "backend\.webapp\Scripts\python.exe" (
    set "PY_CMD=backend\.webapp\Scripts\python.exe"
) else if exist "backend\.venv\Scripts\python.exe" (
    set "PY_CMD=backend\.venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        set "PY_CMD=python"
    ) else (
        where py >nul 2>nul
        if !errorlevel! equ 0 (
            set "PY_CMD=py"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python was not found on this computer.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo or run setup_offline_env.bat first.
    echo.
    pause
    exit /b 1
)

:: 2. Check if frontend is built
if not exist "frontend\dist\index.html" (
    echo [*] Pre-compiled frontend not found. Attempting to build...
    where npm >nul 2>nul
    if !errorlevel! equ 0 (
        cd frontend
        call npm run build
        cd ..
    ) else (
        echo [WARNING] npm is not installed and frontend\dist is missing.
        echo If you downloaded the offline zip, frontend\dist should already be included.
    )
)

echo [*] Starting Live Spreadsheet on http://localhost:8000 ...
echo [*] No internet connection required.
echo [*] Press Ctrl+C in this terminal window to stop the application anytime.
echo.

:: 3. Run the local launcher
"%PY_CMD%" run_local.py

if !errorlevel! neq 0 (
    echo.
    echo [!] Server exited with an error.
    pause
)


