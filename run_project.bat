@echo off
title YOLO11s Weapon Detection AI System
echo ========================================================
echo   Starting YOLO11s Weapon Detection AI System...
echo ========================================================
cd /d "%~dp0"
set KMP_DUPLICATE_LIB_OK=TRUE

:: Select Anaconda Python or fallback to system python
set PYTHON_CMD=C:\Users\DELL\anaconda3\python.exe
if not exist "%PYTHON_CMD%" (
    set PYTHON_CMD=python
)

:: Automatically launch default browser to the web app
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000"

echo Loading AI Model and starting web app at http://127.0.0.1:8000 ...
echo (Your browser will automatically open in a moment!)
echo ========================================================
echo.
"%PYTHON_CMD%" backend.py
pause
