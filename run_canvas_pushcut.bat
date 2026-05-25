@echo off
setlocal

rem Run in project directory
cd /d "%~dp0"

rem Use the project's virtual environment Python
".venv\Scripts\python.exe" "canvas_pushcut.py"

rem Keep window open to read output
echo.
echo Press any key to close...
pause >nul
