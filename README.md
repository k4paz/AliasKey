# HME Hotkey

This project builds one Windows executable:

- `dist\hme.exe`: runs in the system tray, listens for `Ctrl+Win+Alt+H`, creates an HME alias, and copies it to the clipboard. The tray menu opens the cookie editor and can generate an alias or quit.

## Showcase

![HME demo](showcase/hme.gif)

The project does not read browser cookies, passwords, or browser storage. Apple session values expire and must be supplied by the account owner.

## Setup

1. Run `dist\hme.exe`.
2. Select **Edit cookies** from its tray menu.
3. In the editor, select **Open iCloud in browser** and sign in manually.
4. Paste `NAME=VALUE` lines or import a browser-export JSON array. `APPLE_CLIENT_ID` is generated automatically; `APPLE_WEB_ID` is optional.
5. Select **Save session**. The running tray app reads the saved user values on each request, so edits take effect without restarting it.

Values are stored under the current Windows user's environment registry key. Use **Remove session** in the editor to delete them. The executable does not bundle your credentials. Do not share your environment values or cookie exports.

## Install

Download and run `HME-Setup.exe` from the private repository's Releases page. The per-user installer offers a checked **Start HME when I sign in to Windows** option; you can clear it during setup. It adds Start Menu shortcuts and removes them when uninstalled.

The standalone `hme.exe` is also available on the Releases page.

## Build

From this directory run:

```powershell
python -m pip install -r requirements.txt
build.bat
```

The build produces `dist\hme.exe` and `dist\HME-Setup.exe`. Install Inno Setup 6 to compile the installer.
The tray and executable use the authorized artwork in `assets\hme.png` and `assets\hme.ico`; the Tkinter editor uses the same window icon.

## Security

Never commit or distribute Apple session values or cookie exports. If a token was previously stored in this project or shared elsewhere, revoke or rotate it through Apple, then use **Remove session** in the HME editor to clear saved values.