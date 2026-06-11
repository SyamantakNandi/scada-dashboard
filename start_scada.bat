@echo off
chcp 65001 > nul 2>&1
title SCADA Industrial Dashboard

python --version > nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found!
    echo  Please install Python 3.11 from https://python.org/downloads
    echo  IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    pause
    start https://python.org/downloads
    exit /b
)

cd /d "%~dp0"
python launcher.py
pause
