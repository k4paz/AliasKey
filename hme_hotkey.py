"""Apple Hide My Email hotkey daemon."""

import json
import os
import subprocess
import sys
import threading
from datetime import datetime

import keyboard
import pyperclip
import requests
import winreg

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

try:
    import pystray
    from PIL import Image

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


BASE_URL = "https://p164-maildomainws.icloud.com"
REQUEST_TIMEOUT = 20
REQUIRED_CREDENTIALS = (
    "APPLE_DSID",
    "APPLE_CLIENT_ID",
    "APPLE_WEBAUTH_USER",
    "APPLE_WEB_KB",
    "APPLE_HSA_TRUST",
    "APPLE_PCS_EVENTS",
    "APPLE_PCS_DOCUMENTS",
    "APPLE_PCS_PHOTOS",
    "APPLE_PCS_CLOUDKIT",
    "APPLE_PCS_SAFARI",
    "APPLE_PCS_MAIL",
    "APPLE_PCS_NOTES",
    "APPLE_PCS_NEWS",
    "APPLE_PCS_SHARING",
    "APPLE_DS_WEB_SESSION_TOKEN",
    "APPLE_WEBAUTH_VALIDATE",
    "APPLE_WEBAUTH_TOKEN",
)
CONFIGURATION_NAMES = (
    *REQUIRED_CREDENTIALS,
    "APPLE_WEB_ID",
    "APPLE_GROUP",
    "APPLE_CLIENT_BUILD",
    "APPLE_CLIENT_MASTERING",
)


class CredentialError(Exception):
    """Raised when current Apple session values are not configured."""


class RateLimitError(Exception):
    def __init__(self, message: str, retry_after_minutes):
        super().__init__(message)
        self.retry_after_minutes = retry_after_minutes


class UnauthorizedError(Exception):
    """Raised when Apple rejects the current session."""


def _read_user_environment() -> dict:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ,
        ) as key:
            values = {}
            for name in CONFIGURATION_NAMES:
                try:
                    values[name] = winreg.QueryValueEx(key, name)[0]
                except FileNotFoundError:
                    continue
            return values
    except FileNotFoundError:
        return {}


def _toast(title: str, message: str) -> None:
    try:
        from winotify import Notification, audio

        notification = Notification(app_id="HME Hotkey", title=title, msg=message)
        notification.set_audio(audio.Default, loop=False)
        notification.show()
        return
    except Exception:
        pass
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {title}: {message}")


def _load_credentials() -> tuple[dict, dict]:
    saved_values = _read_user_environment()

    def get_value(name: str, default=None):
        if name in saved_values:
            return saved_values[name]
        return os.environ.get(name, default)

    missing = [name for name in REQUIRED_CREDENTIALS if not get_value(name)]
    if missing:
        raise CredentialError(
            "Missing Apple session values. Choose Edit cookies from the HME "
            "tray menu and enter your own values."
        )

    params = {
        "clientBuildNumber": get_value("APPLE_CLIENT_BUILD", "2628Build19"),
        "clientMasteringNumber": get_value(
            "APPLE_CLIENT_MASTERING", "2628Build19"
        ),
        "clientId": get_value("APPLE_CLIENT_ID"),
        "dsid": get_value("APPLE_DSID"),
    }
    cookies = {
        "X-APPLE-WEBAUTH-USER": get_value("APPLE_WEBAUTH_USER"),
        "X_APPLE_WEB_KB-GAWP9W4NANZHON0GZUKJCDJFSS4": get_value("APPLE_WEB_KB"),
        "X-APPLE-WEBAUTH-HSA-TRUST": get_value("APPLE_HSA_TRUST"),
        "X-APPLE-WEBAUTH-PCS-Events": get_value("APPLE_PCS_EVENTS"),
        "X-APPLE-WEBAUTH-PCS-Documents": get_value("APPLE_PCS_DOCUMENTS"),
        "X-APPLE-WEBAUTH-PCS-Photos": get_value("APPLE_PCS_PHOTOS"),
        "X-APPLE-WEBAUTH-PCS-Cloudkit": get_value("APPLE_PCS_CLOUDKIT"),
        "X-APPLE-WEBAUTH-PCS-Safari": get_value("APPLE_PCS_SAFARI"),
        "X-APPLE-WEBAUTH-PCS-Mail": get_value("APPLE_PCS_MAIL"),
        "X-APPLE-WEBAUTH-PCS-Notes": get_value("APPLE_PCS_NOTES"),
        "X-APPLE-WEBAUTH-PCS-News": get_value("APPLE_PCS_NEWS"),
        "X-APPLE-WEBAUTH-PCS-Sharing": get_value("APPLE_PCS_SHARING"),
        "X-APPLE-DS-WEB-SESSION-TOKEN": get_value("APPLE_DS_WEB_SESSION_TOKEN"),
        "x-apple-group": get_value("APPLE_GROUP", "false"),
        "X-APPLE-WEBAUTH-VALIDATE": get_value("APPLE_WEBAUTH_VALIDATE"),
        "X-APPLE-WEBAUTH-TOKEN": get_value("APPLE_WEBAUTH_TOKEN"),
    }
    if get_value("APPLE_WEB_ID"):
        cookies["X-APPLE-WEB-ID"] = get_value("APPLE_WEB_ID")
    return params, cookies


HEADERS = {
    "Content-Type": "text/plain",
    "Accept": "*/*",
    "Origin": "https://www.icloud.com",
    "Referer": "https://www.icloud.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36",
}
LOCK = threading.Lock()


def _post(path: str, payload: dict) -> dict:
    params, cookies = _load_credentials()
    response = requests.post(
        f"{BASE_URL}{path}",
        params=params,
        headers=HEADERS,
        cookies=cookies,
        data=json.dumps(payload),
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code in (401, 403):
        raise UnauthorizedError(
            "Apple rejected the session. Choose Edit cookies from the HME "
            "tray menu and enter fresh values."
        )
    response.raise_for_status()
    data = response.json()
    if "errorMessage" in data:
        raise RateLimitError(data["errorMessage"], data.get("retryAfter"))
    return data


def _generate() -> str:
    data = _post("/v1/hme/generate", {"langCode": "el-gr"})
    hme = data.get("result", {}).get("hme") or data.get("hme")
    if not hme:
        raise ValueError(f"Unexpected generate response: {data}")
    return hme


def _reserve(hme: str) -> None:
    _post("/v1/hme/reserve", {"hme": hme, "label": "Hotkey", "note": ""})


def _on_hotkey() -> None:
    if not LOCK.acquire(blocking=False):
        return
    try:
        _toast("HME", "Generating alias...")
        hme = _generate()
        _reserve(hme)
        pyperclip.copy(hme)
        _toast("HME copied", hme)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Copied: {hme}")
    except RateLimitError as error:
        message = (
            f"Rate limit hit. Retry in {error.retry_after_minutes} min."
            if error.retry_after_minutes
            else "Rate limit hit."
        )
        _toast("HME rate limited", message)
    except (CredentialError, UnauthorizedError) as error:
        _toast("HME authorization", str(error))
    except requests.exceptions.Timeout:
        _toast("HME timeout", "Request timed out. Check your connection.")
    except requests.exceptions.ConnectionError:
        _toast("HME connection", "Cannot reach iCloud. Check your connection.")
    except Exception as error:
        _toast("HME error", str(error)[:120])
    finally:
        LOCK.release()


def _make_tray_icon():
    app_root = getattr(
        sys,
        "_MEIPASS",
        os.path.dirname(os.path.abspath(__file__)),
    )
    icon_path = os.path.join(app_root, "assets", "hme.png")
    with Image.open(icon_path) as image:
        return image.convert("RGBA").resize(
            (64, 64),
            Image.Resampling.LANCZOS,
        )


def _open_setup() -> None:
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--setup"]
    else:
        command = [sys.executable, os.path.abspath(__file__), "--setup"]

    try:
        subprocess.Popen(
            command,
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as error:
        _toast("HME setup", f"Could not open the cookie editor: {error}")


def _run_tray() -> None:
    icon = pystray.Icon(
        "hme_hotkey",
        _make_tray_icon(),
        "HME Hotkey (Ctrl+Win+Alt+H)",
        menu=pystray.Menu(
            pystray.MenuItem(
                "Edit cookies",
                lambda: _open_setup(),
                default=True,
            ),
            pystray.MenuItem("Generate now", lambda: threading.Thread(target=_on_hotkey, daemon=True).start()),
            pystray.MenuItem("Quit", lambda: icon.stop()),
        ),
    )
    icon.run()


def main() -> None:
    if "--setup" in sys.argv[1:]:
        from hme_setup import main as setup_main

        setup_main()
        return

    keyboard.add_hotkey("ctrl+windows+alt+h", _on_hotkey, suppress=False)
    print("HME Hotkey ready: Ctrl+Win+Alt+H")
    _toast("HME Hotkey ready", "Ctrl+Win+Alt+H -> generate alias")
    if TRAY_AVAILABLE:
        _run_tray()
    else:
        keyboard.wait()


if __name__ == "__main__":
    main()