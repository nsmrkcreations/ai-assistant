@echo off
title AI Assistant Desktop - Portable
echo Starting AI Assistant Desktop (Portable Version)...

REM Set up portable Python environment
set "PYTHONPATH=%~dp0python"
set "PATH=%~dp0python;%~dp0python\Scripts;%PATH%"

REM Check if portable Python exists
if not exist "%~dp0python\python.exe" (
    echo Setting up portable Python environment...
    echo This only needs to be done once.
    
    REM Create python directory
    mkdir python 2>nul
    
    echo Please download Python 3.11+ embeddable package from:
    echo https://www.python.org/downloads/windows/
    echo.
    echo Extract it to the 'python' folder in this directory
    echo Then run this launcher again.
    echo.
    pause
    exit /b 1
)

REM Install pip if not present
if not exist "%~dp0python\Scripts\pip.exe" (
    echo Installing pip...
    "%~dp0python\python.exe" -m ensurepip --upgrade
)

REM Install dependencies
echo Installing/updating dependencies...
"%~dp0python\python.exe" -m pip install --upgrade pip
"%~dp0python\python.exe" -m pip install fastapi uvicorn[standard] websockets aiofiles python-multipart aiosqlite cryptography psutil requests

REM Start application
"%~dp0python\python.exe" launch_production.py

pause
