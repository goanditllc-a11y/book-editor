@echo off
title Book Editor - Launcher
echo ============================================
echo        Book Editor - Starting Up...
echo ============================================
echo.

REM ---- Configuration ----
set APP_PORT=5000

REM ---- Detect Python ----
where python >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON=python
    goto :found_python
)
where python3 >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON=python3
    goto :found_python
)
echo ERROR: Python was not found on your PATH.
echo Please install Python from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:found_python

REM ---- Create virtual environment if needed ----
if not exist "venv\" (
    echo Setting up virtual environment...
    %PYTHON% -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM ---- Activate virtual environment ----
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM ---- Install dependencies if marker file is absent ----
if not exist "venv\.deps_installed" (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo. > venv\.deps_installed
)

REM ---- Open browser after a short delay ----
echo Starting Book Editor...
start /b cmd /c "timeout /t 2 >nul && start http://localhost:%APP_PORT%"

REM ---- Launch the app ----
python app.py

REM ---- Pause on unexpected exit so the user can read any error ----
echo.
echo Book Editor has stopped. Press any key to close this window.
pause >nul
