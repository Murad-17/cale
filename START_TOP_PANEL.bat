@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto launch
call INSTALL.bat
if errorlevel 1 goto fail
:launch
".venv\Scripts\python.exe" main.py --desktop --panel-only
if errorlevel 1 goto fail
exit /b 0
:fail
echo ORION could not start. See YUXARI_PANEL_AZ.md for instructions.
pause
exit /b 1
