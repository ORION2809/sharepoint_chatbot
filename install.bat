@echo off
title SharePoint Chatbot - Installer
color 0B
echo ============================================================
echo    SharePoint Chatbot - One-Click Setup
echo ============================================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo         Download from: https://www.python.org/downloads/
    echo.
    echo         IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    echo         After installing Python, run this script again.
    echo.
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)

:: Check Python version (need 3.10+)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo       Python %PYVER% found.
echo.

:: Detect setup mode — GUI wizard or headless
if "%1"=="--headless" goto :headless_install

:: ── GUI Setup Wizard (default) ──────────────────────────────────
echo Starting Setup Wizard...
echo.
python setup_wizard.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Setup complete! Run start.bat to launch the chatbot.
    pause
    exit /b 0
)
echo.
echo [INFO] Setup wizard closed. Falling back to command-line setup...
echo.

:headless_install
:: ── Headless / CLI mode ─────────────────────────────────────────
echo [1/4] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Virtual environment created.
) else (
    echo       Virtual environment already exists.
)

echo.
echo [2/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo       Dependencies installed.

echo.
echo [3/4] Checking configuration...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo       Created .env from template.
    )
    :: Check if .env has real values or just placeholders
    findstr /C:"your-" .env >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo [WARNING] .env contains placeholder values!
        echo           Please ask your IT admin for the correct credentials,
        echo           or run: python setup_wizard.py
        echo.
        pause
        exit /b 1
    )
) else (
    echo       .env found.
)

echo.
echo [4/4] Signing into SharePoint...
echo       A browser window will open for authentication.
echo       Sign in with your Office 365 email.
echo.
python login.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Login may have failed. You can retry with:
    echo           venv\Scripts\python login.py
)

echo.
echo ============================================================
echo    Setup complete! Run start.bat to launch the chatbot.
echo ============================================================
pause
