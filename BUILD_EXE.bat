@echo off
title Building Split Fighter Executable
echo ============================================
echo   Building Standalone Windows Executable
echo ============================================
echo.

cd /d "%~dp0"

echo [1/2] Installing requirements...
pip install pygame requests pyinstaller --quiet

echo [2/2] Running PyInstaller...
pyinstaller --noconfirm --onedir --windowed --name "SplitFighter" --add-data "config.json;." main.py

echo.
echo ============================================
echo   BUILD COMPLETE!
echo   Folder: dist\SplitFighter\SplitFighter.exe
echo ============================================
pause
