@echo off
title 🚀 PRINCE OTP BOT - 1-CLICK RDP SETUP & RUNNER
color 0A
chcp 65001 >nul

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ================================================================
echo       👑 PRINCE OTP BOT + IVASMS FETCHER - RDP SETUP
echo ================================================================
echo.

:: 1. Check Python
echo [1/3] 🔍 Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo ❌ ERROR: Python is not installed or not in PATH!
    echo 👉 Download: https://www.python.org/downloads/
    echo ⚠️ Check 'Add Python to PATH' during installation!
    pause
    exit /b
)
python --version
echo ✅ Python detected.
echo.

:: 2. Install Dependencies
echo [2/3] 📦 Installing required libraries...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ⚠️ Attempting direct install...
    python -m pip install python-telegram-bot curl_cffi cloudscraper
)
echo ✅ All libraries ready!
echo.

:: 3. Launch System
echo [3/3] 🚀 Launching Bot + ivasms OTP Fetcher...
echo ================================================================
echo 💡 Press Ctrl+C to stop.
echo ================================================================
echo.

:RUN_LOOP
python run_all.py
echo.
echo ================================================================
echo ⚠️ System stopped. Restarting in 5 seconds... (Ctrl+C to cancel)
echo ================================================================
timeout /t 5 >nul
goto RUN_LOOP
