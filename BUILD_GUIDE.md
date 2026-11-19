# Build Guide

## Requirements

- Windows
- Python 3.10 or newer
- Packages from `requirements.txt`
- Inno Setup 6

## Build

Install the requirements, install Inno Setup 6, and run `build.bat` from this directory. It creates:

- `dist\hme.exe` — the tray hotkey app and cookie editor in one executable.
- `dist\HME-Setup.exe` — per-user installer with a selectable startup shortcut.

Use **Edit cookies** in the tray menu to open the setup window. It opens iCloud in the user's browser and processes a JSON file or values manually supplied by the user; it does not inspect browser cookies or passwords automatically. Use **Remove session** in the editor to clear saved values.

The Windows executable and Tkinter setup window use `assets\hme.ico`; the tray uses `assets\hme.png`. Keep both assets in place when building.