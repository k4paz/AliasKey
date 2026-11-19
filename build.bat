@echo off
REM ============================================================================
REM Apple HME - Build Script for Windows
REM Builds one executable:
REM   dist\hme.exe - tray hotkey app and manual cookie editor
REM
REM Prerequisites:
REM   python -m pip install -r requirements.txt
REM ============================================================================

echo.
echo ============================================================================
echo  Apple HME - Build Process
echo ============================================================================
echo.

REM --- Python check ------------------------------------------------------------
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3.10 or newer is required.
    exit /b 1
)

REM --- Dependency check / install ----------------------------------------------
echo [1/4] Checking dependencies...

python -c "import PyInstaller, requests, keyboard, pyperclip, winotify, pystray, PIL" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   - Installing project dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed!
        exit /b 1
    )
)

echo   - All dependencies present.

REM --- Clean previous artifacts -------------------------------------------------
echo [2/4] Cleaning previous build artifacts...
if exist "dist\hme.exe" (
    del /q "dist\hme.exe"
    if exist "dist\hme.exe" (
        echo [ERROR] Could not replace dist\hme.exe. Close HME and retry.
        exit /b 1
    )
)
if exist "dist\hme_hotkey.exe" del /q "dist\hme_hotkey.exe"
if exist "dist\hme_setup.exe" del /q "dist\hme_setup.exe"
echo   - Done.

REM --- Build combined HME app ---------------------------------------------------
echo [3/4] Building hme.exe...
echo.
python -m PyInstaller hme_hotkey.spec --clean
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] hme.exe build failed!
    exit /b 2
)

REM --- Verify outputs -----------------------------------------------------------
echo [4/4] Verifying output file...

if not exist "dist\hme.exe" (
    echo [ERROR] dist\hme.exe not found!
    exit /b 3
)
for %%A in (dist\hme.exe) do echo   - dist\hme.exe (%%~zA bytes^)

echo.
echo ============================================================================
echo  Build Complete!
echo ============================================================================
echo.
echo  dist\hme.exe          - hotkey app, tray, and cookie editor
echo.
echo Next steps:
echo   double-click dist\hme.exe (runs in the system tray)
echo   press Ctrl+Win+Alt+H to generate ^& copy an alias
echo   use tray menu Edit cookies to update session values
echo   stop it with the tray icon Quit option
echo.
echo ============================================================================

exit /b 0
