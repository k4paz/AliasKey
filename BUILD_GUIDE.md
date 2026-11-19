# Build Guide

## Requirements

- Windows
- Python 3.10 or newer
- Packages from `requirements.txt`
- PyInstaller, keyboard, pyperclip, pystray, pillow, and winotify

## Build

Install the requirements and run `build.bat` from this directory. It creates:

- `dist\hme.exe` — the tray hotkey app and cookie editor in one executable.

Use **Edit cookies** in the tray menu to open the setup window. It opens iCloud in the user's browser and processes a JSON file or values manually supplied by the user; it does not inspect browser cookies or passwords automatically.

The Windows executable and Tkinter setup window use `assets\hme.ico`; the tray uses `assets\hme.png`. Keep both assets in place when building.