@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 goto use_python
set "ORION_PY=py -3"
goto check_python
:use_python
set "ORION_PY=python"
:check_python
%ORION_PY% --version
if errorlevel 1 goto missing
if exist ".venv\Scripts\python.exe" goto deps
%ORION_PY% -m venv .venv
if errorlevel 1 goto fail
:deps
".venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt
if errorlevel 1 goto fail
if exist ".env" goto done
copy ".env.example" ".env" >nul
if errorlevel 1 goto fail
echo Copy your API keys into .env and save the file.
start /wait notepad.exe ".env"
:done
echo Installation finished. Open START.bat.
pause
exit /b 0
:missing
echo Python was not found. Install Python 3.11 or newer.
:fail
echo Installation failed. Send a screenshot of this window.
pause
exit /b 1
