@echo off
cd /d "%~dp0"

if not exist "start.py" (
  echo.
  echo  ERROR: start.py is not in this folder.
  echo  You must EXTRACT the ZIP first, then double-click this file
  echo  from INSIDE the extracted folder.
  echo.
  pause
  exit /b
)

where py >nul 2>nul
if %errorlevel%==0 (
  cmd /k py start.py
  exit /b
)

where python >nul 2>nul
if %errorlevel%==0 (
  cmd /k python start.py
  exit /b
)

echo.
echo  ============================================================
echo   PYTHON IS NOT INSTALLED on this computer.
echo.
echo   FIX - 2 minutes:
echo    1. Go to  python.org/downloads
echo    2. Click the big yellow "Download Python" button
echo    3. Run the installer
echo    4. IMPORTANT: on the first screen CHECK the box
echo       "Add Python to PATH"
echo    5. Click "Install Now", wait, then double-click
echo       run-windows.bat again
echo  ============================================================
echo.
pause
