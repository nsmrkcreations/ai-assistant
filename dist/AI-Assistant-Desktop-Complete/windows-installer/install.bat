@echo off
title AI Assistant Desktop - Windows Installer
echo.
echo ========================================
echo   AI Assistant Desktop - Installation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo ✓ Python is already installed
    goto :install_app
)

echo Python is not installed. Installing Python...
echo.

REM Download and install Python
echo Downloading Python installer...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile 'python-installer.exe'}"

if not exist python-installer.exe (
    echo ❌ Failed to download Python installer
    echo Please install Python manually from https://python.org
    pause
    exit /b 1
)

echo Installing Python (this may take a few minutes)...
python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

REM Wait for installation to complete
timeout /t 10 /nobreak >nul

REM Refresh environment variables
call refreshenv.cmd 2>nul || echo Refreshing environment...

REM Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python installation failed
    echo Please restart your computer and run this installer again
    pause
    exit /b 1
)

echo ✓ Python installed successfully

:install_app
echo.
echo Installing AI Assistant Desktop...

REM Install required packages
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn[standard] websockets aiofiles python-multipart aiosqlite cryptography psutil requests

if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✓ Dependencies installed

REM Create desktop shortcut
echo Creating desktop shortcut...
set "desktop=%USERPROFILE%\Desktop"
set "shortcut=%desktop%\AI Assistant.bat"

echo @echo off > "%shortcut%"
echo title AI Assistant Desktop >> "%shortcut%"
echo cd /d "%~dp0" >> "%shortcut%"
echo python launch_production.py >> "%shortcut%"
echo pause >> "%shortcut%"

echo ✓ Desktop shortcut created

REM Start the application
echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo ✓ AI Assistant Desktop is now installed
echo ✓ Desktop shortcut created
echo ✓ Ready to use
echo.
echo Starting AI Assistant Desktop...
echo.

python launch_production.py

pause
