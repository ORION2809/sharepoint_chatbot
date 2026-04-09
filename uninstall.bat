@echo off
title SharePoint Chatbot - Uninstaller
color 0C
echo ============================================================
echo    SharePoint Chatbot - Uninstall
echo ============================================================
echo.
echo This will remove:
echo   - Virtual environment (venv)
echo   - Index database (.chroma_db)
echo   - Cached tokens (.token_cache.json)
echo   - Index metadata (.index_meta.json)
echo   - Configuration (.env)
echo.
echo Your application files (scripts, templates) will NOT be removed.
echo.

set /p CONFIRM="Are you sure you want to uninstall? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Removing virtual environment...
if exist "venv" rmdir /s /q "venv" 2>nul
echo   Done.

echo Removing index database...
if exist ".chroma_db" rmdir /s /q ".chroma_db" 2>nul
echo   Done.

echo Removing cached tokens...
if exist ".token_cache.json" del /f /q ".token_cache.json" 2>nul
echo   Done.

echo Removing index metadata...
if exist ".index_meta.json" del /f /q ".index_meta.json" 2>nul
echo   Done.

echo Removing configuration...
if exist ".env" del /f /q ".env" 2>nul
echo   Done.

echo Removing Python cache...
if exist "__pycache__" rmdir /s /q "__pycache__" 2>nul
echo   Done.

:: Remove desktop shortcut if it exists
if exist "%USERPROFILE%\Desktop\SharePoint Chatbot.lnk" (
    echo Removing desktop shortcut...
    del /f /q "%USERPROFILE%\Desktop\SharePoint Chatbot.lnk" 2>nul
    echo   Done.
)

echo.
echo ============================================================
echo    Uninstall complete.
echo ============================================================
echo.
echo To fully remove, delete this folder:
echo   %~dp0
echo.
pause
