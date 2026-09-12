@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run the setup commands from README.md first.
    exit /b 1
)
".venv\Scripts\python.exe" main.py

