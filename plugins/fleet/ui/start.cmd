@echo off
cd /d "%~dp0\..\..\.."
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 plugins\fleet\main.py serve
) else (
  python plugins\fleet\main.py serve
)
