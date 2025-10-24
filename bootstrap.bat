@echo off
echo --- Bootstrapping Project ---

REM Checks for Python
py -3 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python 3 could not be found. Please install it and add it to your PATH.
    exit /b 1
)

REM Creates virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating Python virtual environment...
    py -3 -m venv .venv
)

REM Installs dependencies
echo Installing dependencies from requirements.txt...
.venv\Scripts\pip.exe install -r requirements.txt

REM Creates .env file from example if it doesn't exist
if not exist ".env" (
    echo Creating .env file from .env.example...
    copy .env.example .env
)

REM Run initial database migrations
echo Running database migrations...
.venv\Scripts\python.exe manage.py migrate

echo.
echo --- Bootstrap complete! ---
echo To start the server, run the following commands:
echo 1. .\.venv\Scripts\activate.ps1 (in PowerShell) OR .\.venv\Scripts\activate.bat (in Command Prompt)
echo 2. py manage.py runserver
