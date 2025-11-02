@echo off
echo ========================================
echo PCOR Setup - Installing Dependencies
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv .venv

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Pulling Ollama vision model (minicpm-v)...
echo This may take a few minutes...
ollama pull minicpm-v

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To run the application:
echo   1. Double-click run.bat
echo   OR
echo   2. Run: .venv\Scripts\activate.bat
echo      Then: python pcor.py
echo.
echo Make sure Ollama is installed and running:
echo   Download from: https://ollama.ai
echo   Then run: ollama pull minicpm-v:2b
echo.
pause
