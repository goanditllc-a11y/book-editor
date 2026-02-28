@echo off
title Book Editor - Setup Desktop Shortcut
echo ============================================
echo    Book Editor - Setting Up Desktop Shortcut
echo ============================================
echo.

REM Resolve the full path to launch.bat in the project root
set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%SCRIPT_DIR%launch.bat"

if not exist "%LAUNCHER%" (
    echo ERROR: launch.bat was not found in "%SCRIPT_DIR%".
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Build path to the user's Desktop
set "SHORTCUT=%USERPROFILE%\Desktop\Book Editor.lnk"

REM Use PowerShell to create the shortcut
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$s = $ws.CreateShortcut('%SHORTCUT%'); " ^
  "$s.TargetPath = '%LAUNCHER%'; " ^
  "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
  "$s.Description = 'Launch Book Editor application'; " ^
  "$s.Save()"

if %errorlevel% neq 0 (
    echo ERROR: Failed to create the desktop shortcut.
    pause
    exit /b 1
)

echo Desktop shortcut "Book Editor" has been created successfully!
echo You can now double-click it to start the application.
echo.
pause
