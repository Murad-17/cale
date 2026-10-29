@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%LOCALAPPDATA%\Roblox\Plugins" mkdir "%LOCALAPPDATA%\Roblox\Plugins"
copy /Y "roblox_plugin\OrionBridge.lua" "%LOCALAPPDATA%\Roblox\Plugins\OrionBridge.lua"
echo Studio-nu yenidən aç, HTTP Requests-i aktiv et və ORION toolbar düyməsini bas.
pause
