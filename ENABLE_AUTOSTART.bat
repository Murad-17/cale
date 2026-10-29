@echo off
chcp 65001 >nul
set "ORION_INSTALL_DIR=%~dp0"
powershell.exe -NoProfile -Command "$root=$env:ORION_INSTALL_DIR; $python=Join-Path $root '.venv\Scripts\pythonw.exe'; if (-not (Test-Path $python)) { Write-Host 'Əvvəl INSTALL.bat işə sal.'; exit 1 }; $shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'ORION.lnk')); $shortcut.TargetPath=$python; $shortcut.Arguments='"'+(Join-Path $root 'main.py')+'" --desktop'; $shortcut.WorkingDirectory=$root; $shortcut.Save()"
echo Avtomatik açılmanı ləğv etmək üçün Windows Startup qovluğundan ORION qısayolunu sil.
pause
