@echo off
setlocal enabledelayedexpansion

title Live Spreadsheet - Offline Environment Setup

echo ======================================================================
echo           LIVE SPREADSHEET - LOCAL ENVIRONMENT SETUP
echo ======================================================================
echo.
echo This script prepares the local Python environment for running
echo Live Spreadsheet completely offline on your PC.
echo.

cd /d "%~dp0"

:: 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11 or newer is required but was not found.
    echo Please download and install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [*] Python found. Setting up local virtual environment...
if not exist "backend\.venv" (
    python -m venv backend\.venv
)

echo [*] Installing backend dependencies into isolated environment...
call backend\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

echo.
echo ======================================================================
echo [SUCCESS] Environment setup complete!
echo You can now double-click "run_app.bat" to start Live Spreadsheet.
echo ======================================================================
echo.
pause
