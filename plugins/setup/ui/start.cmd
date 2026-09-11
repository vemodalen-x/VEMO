@echo off
cd /d "%~dp0.."
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 bin\vemo ui
) else (
  python bin\vemo ui
)
if errorlevel 1 pause
