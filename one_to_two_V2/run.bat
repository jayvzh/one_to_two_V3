@echo off
setlocal

set "VENV_PATH=%~dp0venv"
set "VENV_SCRIPTS=%VENV_PATH%\Scripts"

if exist "%VENV_SCRIPTS%\activate.bat" (
    call "%VENV_SCRIPTS%\activate.bat"
) else (
    echo [Warning] Virtual environment not found at: %VENV_PATH%
    echo [Info] Please run menu option 8 to setup virtual environment first.
    echo.
)

python "%~dp0app\menu.py"
if errorlevel 1 (
    echo.
    echo [Error] Failed to start menu. Please check Python environment.
    pause
)

endlocal
