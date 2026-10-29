@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto launch
call INSTALL.bat
if errorlevel 1 goto fail
:launch
".venv\Scripts\python.exe" main.py --desktop
if errorlevel 1 goto fail
exit /b 0
:fail
echo ORION could not start. Send a screenshot of this window.
pause
exit /b 1
