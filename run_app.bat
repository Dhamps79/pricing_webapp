@echo off
setlocal enabledelayedexpansion

title Live Spreadsheet - Local App

echo ======================================================================
echo                 LIVE SPREADSHEET - 1-CLICK LAUNCHER
echo ======================================================================
echo.

cd /d "%~dp0"

:: Check for virtualenv python
if exist "backend\.webapp\Scripts\python.exe" (
    set "PY_CMD=backend\.webapp\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

:: Check if frontend is built
if not exist "frontend\dist\index.html" (
    echo [*] Frontend distribution not found. Building frontend...
    cd frontend
    call npm run build
    cd ..
)

echo [*] Starting Live Spreadsheet at http://localhost:8000 ...
echo [*] Press Ctrl+C in this window to exit anytime.
echo.

:: Launch the launcher script
"%PY_CMD%" run_local.py

pause

