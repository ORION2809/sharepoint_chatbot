@echo off
title SharePoint Chatbot
color 0B
echo ============================================================
echo    SharePoint Chatbot - Starting...
echo ============================================================
echo.

:: Check virtual environment
if not exist "venv" (
    echo [ERROR] Virtual environment not found.
    echo.
    echo         Run install.bat first to set up the application.
    echo.
    pause
    exit /b 1
)

:: Check .env exists and has real values
if not exist ".env" (
    echo [ERROR] Configuration file .env not found.
    echo         Run install.bat first to set up the application.
    pause
    exit /b 1
)

:: Check token cache — prompt login if missing
if not exist ".token_cache.json" (
    echo [INFO] You haven't signed in yet.
    echo        A browser window will open for authentication.
    echo        Sign in with your Office 365 email.
    echo.
    call venv\Scripts\activate.bat
    python login.py
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Sign-in failed. Please try again.
        pause
        exit /b 1
    )
    echo.
)

call venv\Scripts\activate.bat

echo Starting server at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

:: Open browser after short delay
start "" /min cmd /c "timeout /t 2 >nul & start http://127.0.0.1:8000"

python -m uvicorn main:app --host 127.0.0.1 --port 8000
