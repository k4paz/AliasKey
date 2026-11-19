@echo off
setlocal

echo HME build
echo.

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    exit /b 1
)

python -c "import PyInstaller, requests, keyboard, pyperclip, winotify, pystray, PIL" >nul 2>&1
if errorlevel 1 (
    echo Installing Python build requirements...
    python -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

set "ISCC="
where ISCC.exe >nul 2>&1
if not errorlevel 1 set "ISCC=ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo ERROR: Inno Setup 6 is required to build the installer.
    echo Install it from https://jrsoftware.org/isdl.php and retry.
    exit /b 1
)

if not exist "dist" mkdir "dist"
if exist "dist\hme.exe" (
    del /q "dist\hme.exe"
    if exist "dist\hme.exe" (
        echo ERROR: Close HME before rebuilding.
        exit /b 1
    )
)
if exist "dist\HME-Setup.exe" del /q "dist\HME-Setup.exe"
if exist "dist\hme-setup.exe" del /q "dist\hme-setup.exe"
if exist "dist\hme_hotkey.exe" del /q "dist\hme_hotkey.exe"
if exist "dist\hme_setup.exe" del /q "dist\hme_setup.exe"

python -m PyInstaller hme_hotkey.spec --clean
if errorlevel 1 exit /b 2
if not exist "dist\hme.exe" (
    echo ERROR: PyInstaller did not produce dist\hme.exe.
    exit /b 2
)

"%ISCC%" "installer\hme.iss"
if errorlevel 1 exit /b 3
if not exist "dist\HME-Setup.exe" (
    echo ERROR: Inno Setup did not produce dist\HME-Setup.exe.
    exit /b 3
)

echo.
echo Build complete:
echo   dist\hme.exe
echo   dist\HME-Setup.exe
exit /b 0
