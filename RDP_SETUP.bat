@echo off
title 🚀 PRINCE OTP BOT - 1-CLICK RDP SETUP & RUNNER
color 0A
chcp 65001 >nul

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ================================================================
echo       👑 PRINCE OTP BOT & USERBOT FORWARDER - RDP SETUP
echo ================================================================
echo.

:: 1. Check Python Installation
echo [1/3] 🔍 Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ❌ ERROR: Python is not installed or not in PATH!
    echo 👉 Please download and install Python from https://www.python.org/downloads/
    echo ⚠️ Make sure to CHECK 'Add Python to PATH' during installation!
    echo.
    pause
    exit /b
)
python --version
echo ✅ Python is installed and detected.
echo.

:: 2. Upgrade pip and Install Dependencies
echo [2/3] 📦 Installing and upgrading required libraries...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ⚠️ Warning occurred during pip install, attempting direct install...
    python -m pip install python-telegram-bot telethon
)
echo ✅ All required libraries are ready!
echo.

:: 3. Launch the Master Runner System
echo [3/3] 🚀 Launching Bot and Userbot Forwarder...
echo ================================================================
echo 💡 System is starting. To stop at any time, press Ctrl + C.
echo ================================================================
echo.
python run_all.py

pause
