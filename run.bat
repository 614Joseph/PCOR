@echo off
echo Starting PCOR - Screenshot OCR Application...
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run setup.bat first.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Warning: Ollama does not appear to be running.
    echo Please start Ollama and ensure you have pulled the model:
    echo   ollama pull minicpm-v:2b
    echo.
    echo Attempting to start anyway...
    echo.
)

REM Run the application
python pcor.py

REM Deactivate when done
call deactivate

pause
