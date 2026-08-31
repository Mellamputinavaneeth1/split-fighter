@echo off
title SPLIT FIGHTER
echo.
echo  ====================================
echo      SPLIT FIGHTER - Game Launcher
echo  ====================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed!
    echo.
    echo  Download it from: https://www.python.org/downloads/
    echo  IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo  [1/2] Installing dependencies...
pip install pygame requests --quiet 2>nul
echo        Done.
echo.
echo  [2/2] Starting game...
echo.

:: Run the game from the script's directory
cd /d "%~dp0"
python main.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Game crashed. Check the error above.
    pause
)
