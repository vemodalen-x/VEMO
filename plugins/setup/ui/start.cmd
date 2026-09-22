@echo off
cd /d "%~dp0..\.."
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 plugins\setup\entry.py ui
) else (
  python plugins\setup\entry.py ui
)
if errorlevel 1 pause
