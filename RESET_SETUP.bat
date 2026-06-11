@echo off
title SCADA - Reset Setup
echo.
echo  This resets the launcher config (not your data).
echo.
set /p c="Type YES to confirm: "
if /i not "%c%"=="YES" ( echo Cancelled. & pause & exit /b )
cd /d "%~dp0"
if exist launcher_config.json del launcher_config.json
echo  Config cleared. Running setup again...
python launcher.py
pause
