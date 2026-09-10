@echo off
setlocal
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "VEMO_ROOT="
set "PATH=%~dp0runtime;%PATH%"
if /I "%~1"=="shell" (
  echo VEMO shell: private Python runtime is active for this window only.
  cmd /K
  exit /b
)
if "%~1"=="" (
  "%~dp0runtime\python.exe" -X utf8 -S "%~dp0framework\bin\vemo" ui
) else (
  "%~dp0runtime\python.exe" -X utf8 -S "%~dp0framework\bin\vemo" %*
)
exit /b %errorlevel%
