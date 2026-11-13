@echo off
setlocal
cd /d "%~dp0"

if not exist "start.py" (
    echo.
    echo  ERROR: start.py not found in this folder.
    echo  You must EXTRACT the ZIP first, then double-click this file
    echo  from INSIDE the extracted folder.
    echo.
    pause
    exit /b 1
)

set RUNNER=

where py >nul 2>nul
if not errorlevel 1 set RUNNER=py

if not defined RUNNER (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys" >nul 2>nul
        if not errorlevel 1 set RUNNER=python
    )
)

if defined RUNNER goto :run

echo.
echo  Python is not installed. Trying to install it automatically...
echo  (needs internet, takes about a minute - DO NOT close this window)
echo.

where winget >nul 2>nul
if errorlevel 1 goto :manual

winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :manual

set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Launcher"

where py >nul 2>nul
if not errorlevel 1 (
    set RUNNER=py
    goto :run
)

where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set RUNNER=python
        goto :run
    )
)

:manual
echo.
echo  ============================================================
echo   Could not install Python automatically.
echo.
echo   DO THIS - takes 2 minutes:
echo    1. Open   python.org/downloads
echo    2. Click the big yellow "Download Python" button
echo    3. Run the downloaded file
echo    4. On the first screen CHECK the box "Add Python to PATH"
echo    5. Click "Install Now" and wait for it to finish
echo    6. Then double-click run-windows.bat again
echo  ============================================================
echo.
pause
exit /b 1

:run
cmd /k %RUNNER% start.py
