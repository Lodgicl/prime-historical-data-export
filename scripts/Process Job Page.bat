@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo Prime Job Batch Runner
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo.
    pause
    exit /b 1
)

python -c "import requests" >nul 2>nul
if errorlevel 1 (
    echo Installing required Python package: requests
    python -m pip install requests
    if errorlevel 1 (
        echo ERROR: Failed to install requests.
        echo.
        pause
        exit /b 1
    )
)

echo Running orchestrator...
echo.

python "%~dp0prime_run_job_batch.py"

echo.
pause
endlocal