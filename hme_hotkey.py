"""HME tray app, alias hotkey, and session editor."""

import json
import math
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime
import webbrowser

import keyboard
import pyperclip
import requests
import tkinter as tk
import winreg
from tkinter import filedialog, messagebox

try:
    import pystray
    from PIL import Image

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


BASE_URL = "https://p164-maildomainws.icloud.com"
REQUEST_TIMEOUT = 20
REQUIRED_FIELDS = (
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
REQUIRED_CREDENTIALS = REQUIRED_FIELDS
OPTIONAL_DEFAULTS = {
    "APPLE_WEB_ID": "",
    "APPLE_GROUP": "false",
    "APPLE_CLIENT_BUILD": "2628Build19",
    "APPLE_CLIENT_MASTERING": "2628Build19",
}
COOKIE_ENV_NAMES = {
    "X-APPLE-WEBAUTH-USER": "APPLE_WEBAUTH_USER",
    "X_APPLE_WEB_KB-GAWP9W4NANZHON0GZUKJCDJFSS4": "APPLE_WEB_KB",
    "X-APPLE-WEBAUTH-HSA-TRUST": "APPLE_HSA_TRUST",
    "X-APPLE-DS-WEB-SESSION-TOKEN": "APPLE_DS_WEB_SESSION_TOKEN",
    "X-APPLE-WEB-ID": "APPLE_WEB_ID",
    "x-apple-group": "APPLE_GROUP",
    "X-APPLE-WEBAUTH-VALIDATE": "APPLE_WEBAUTH_VALIDATE",
    "X-APPLE-WEBAUTH-TOKEN": "APPLE_WEBAUTH_TOKEN",
}
for _service in (
    "Events",
    "Documents",
    "Photos",
    "Cloudkit",
    "Safari",
    "Mail",
    "Notes",
    "News",
    "Sharing",
):
    COOKIE_ENV_NAMES[f"X-APPLE-WEBAUTH-PCS-{_service}"] = f"APPLE_PCS_{_service.upper()}"

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


def _unwrap_cookie_value(value: object) -> str:
    value = str(value).strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        try:
            decoded = json.loads(value)
            if isinstance(decoded, str):
                return decoded
        except json.JSONDecodeError:
            pass
    return value


def cookie_json_to_values(cookie_json: str | list[dict]) -> dict[str, str]:
    cookies = json.loads(cookie_json) if isinstance(cookie_json, str) else cookie_json
    if not isinstance(cookies, list):
        raise ValueError("Cookie JSON must be an array of cookie objects.")

    values = {}
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = cookie.get("name")
        if name in COOKIE_ENV_NAMES and "value" in cookie:
            values[COOKIE_ENV_NAMES[name]] = _unwrap_cookie_value(cookie["value"])

    dsid_match = re.search(
        r"(?:^|:)d=([^:;]+)",
        values.get("APPLE_WEBAUTH_USER", ""),
    )
    if dsid_match:
        values["APPLE_DSID"] = dsid_match.group(1)
    return values


def values_to_text(values: dict[str, str]) -> str:
    merged = {**OPTIONAL_DEFAULTS, **values}
    merged["APPLE_CLIENT_ID"] = (
        merged.get("APPLE_CLIENT_ID")
        or os.environ.get("APPLE_CLIENT_ID")
        or str(uuid.uuid4())
    )
    return "\n".join(
        f"{name}={merged.get(name, '')}"
        for name in (*REQUIRED_FIELDS, *OPTIONAL_DEFAULTS)
    )


def text_to_values(raw_text: str) -> dict[str, str]:
    if raw_text.lstrip().startswith("["):
        values = cookie_json_to_values(raw_text)
        values["APPLE_CLIENT_ID"] = (
            os.environ.get("APPLE_CLIENT_ID") or str(uuid.uuid4())
        )
        return values

    values = {}
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name in REQUIRED_FIELDS or name in OPTIONAL_DEFAULTS:
            values[name] = value.strip()
    return values


def _save_user_values(values: dict[str, str]) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        for name, value in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            os.environ[name] = value


def _remove_saved_values() -> list[str]:
    failures = []
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            for name in CONFIGURATION_NAMES:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
                except OSError:
                    failures.append(name)
                os.environ.pop(name, None)
    except OSError as error:
        raise OSError(f"Could not open the user environment registry key: {error}") from error
    return failures


def _broadcast_environment_change() -> None:
    import ctypes

    result = ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF,
        0x001A,
        0,
        "Environment",
        0x0002,
        5000,
        None,
    )
    if not result:
        raise OSError("Windows did not confirm the environment update broadcast.")


BG_CANVAS = "#F5F6F7"
BG_SURFACE = "#FCFCFD"
BG_SUBTLE = "#F2F1EF"
ACCENT_LIME = "#C2FA28"
TRACK_MUTED = "#E6E7E8"
INK_PRIMARY = "#111111"
INK_SECONDARY = "#6E7175"
INK_MUTED = "#9A9D9E"


def _rounded_rectangle_points(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
) -> list[float]:
    radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = []
    for center_x, center_y, start_angle in (
        (x2 - radius, y1 + radius, -90),
        (x2 - radius, y2 - radius, 0),
        (x1 + radius, y2 - radius, 90),
        (x1 + radius, y1 + radius, 180),
    ):
        for step in range(7):
            angle = math.radians(start_angle + step * 15)
            points.extend(
                (
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                )
            )
    return points


def _rounded_rectangle(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    **kwargs: object,
) -> int:
    return canvas.create_polygon(
        _rounded_rectangle_points(x1, y1, x2, y2, radius),
        smooth=False,
        **kwargs,
    )


def setup_main() -> None:
    root = tk.Tk()
    root.title("HME | Hide My Email")
    root.geometry("800x760")
    root.minsize(640, 600)
    root.configure(bg=BG_CANVAS)
    app_root = getattr(
        sys,
        "_MEIPASS",
        os.path.dirname(os.path.abspath(__file__)),
    )
    root.iconbitmap(os.path.join(app_root, "assets", "hme.ico"))

    header = tk.Frame(root, bg=BG_CANVAS)
    header.pack(fill="x", padx=30, pady=(26, 18))
    tk.Label(
        header,
        text="Hide My Email",
        bg=BG_CANVAS,
        fg=INK_PRIMARY,
        font=("Segoe UI", 22, "bold"),
    ).pack(anchor="w")
    tk.Label(
        header,
        text="Create a private alias and copy it with a keyboard shortcut.",
        bg=BG_CANVAS,
        fg=INK_SECONDARY,
        font=("Segoe UI", 10),
    ).pack(anchor="w", pady=(3, 0))

    card_canvas = tk.Canvas(
        root,
        bg=BG_CANVAS,
        highlightthickness=0,
        bd=0,
    )
    card_canvas.pack(fill="both", expand=True, padx=22, pady=(0, 22))
    card = tk.Frame(card_canvas, bg=BG_SURFACE)
    card_window = card_canvas.create_window(
        24,
        24,
        anchor="nw",
        window=card,
    )
    card_background = _rounded_rectangle(
        card_canvas,
        1,
        1,
        100,
        100,
        24,
        fill=BG_SURFACE,
        outline="#E9EAEB",
        width=1,
    )
    card_canvas.tag_lower(card_background, card_window)

    def resize_card(event: tk.Event) -> None:
        card_canvas.coords(
            card_background,
            *_rounded_rectangle_points(
                1,
                1,
                event.width - 1,
                event.height - 1,
                24,
            ),
        )
        card_canvas.coords(card_window, 24, 24)
        card_canvas.itemconfigure(
            card_window,
            width=max(1, event.width - 48),
            height=max(1, event.height - 48),
        )

    card_canvas.bind("<Configure>", resize_card)

    content = tk.Frame(card, bg=BG_SURFACE)
    content.pack(fill="both", expand=True, padx=28, pady=26)
    tk.Label(
        content,
        text="Connect your Apple session",
        bg=BG_SURFACE,
        fg=INK_PRIMARY,
        font=("Segoe UI", 17, "bold"),
    ).pack(anchor="w")
    tk.Label(
        content,
        text=(
            "Sign in manually, then paste your session values or import a cookie "
            "JSON export. HME does not read browser data."
        ),
        bg=BG_SURFACE,
        fg=INK_SECONDARY,
        justify="left",
        wraplength=680,
    ).pack(anchor="w", pady=(5, 18))

    def make_button(
        parent: tk.Widget,
        label: str,
        *,
        background: str,
        foreground: str = INK_PRIMARY,
        command=None,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=label,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=background,
            activeforeground=foreground,
            relief="flat",
            bd=0,
            padx=16,
            pady=10,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            highlightthickness=0,
        )

    make_button(
        content,
        "Open iCloud in browser",
        background=BG_SUBTLE,
        command=lambda: webbrowser.open("https://www.icloud.com/"),
    ).pack(anchor="w", pady=(0, 20))

    input_header = tk.Frame(content, bg=BG_SURFACE)
    input_header.pack(fill="x", pady=(0, 8))
    tk.Label(
        input_header,
        text="Session values",
        bg=BG_SURFACE,
        fg=INK_PRIMARY,
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left")

    def import_json_file() -> None:
        filename = filedialog.askopenfilename(
            title="Select cookie JSON export",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as cookie_file:
                values = cookie_json_to_values(cookie_file.read())
            if not values:
                raise ValueError("No recognized Apple cookies were found.")
            text.delete("1.0", "end")
            text.insert("1.0", values_to_text(values))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Could not import JSON", str(error))

    make_button(
        input_header,
        "Import cookie JSON",
        background=BG_SUBTLE,
        command=import_json_file,
    ).pack(side="right")

    editor = tk.Frame(
        content,
        bg="#FFFFFF",
        highlightbackground=TRACK_MUTED,
        highlightthickness=1,
    )
    editor.pack(fill="both", expand=True)
    text = tk.Text(
        editor,
        wrap="none",
        undo=True,
        bg="#FFFFFF",
        fg=INK_PRIMARY,
        insertbackground=INK_PRIMARY,
        selectbackground=ACCENT_LIME,
        selectforeground=INK_PRIMARY,
        relief="flat",
        bd=0,
        padx=12,
        pady=10,
        font=("Consolas", 9),
        xscrollcommand=lambda first, last: horizontal_scrollbar.set(first, last),
        yscrollcommand=lambda first, last: vertical_scrollbar.set(first, last),
    )
    vertical_scrollbar = tk.Scrollbar(
        editor,
        orient="vertical",
        command=text.yview,
        relief="flat",
        bd=0,
        bg=BG_SURFACE,
        activebackground=INK_MUTED,
        troughcolor=BG_SURFACE,
        width=12,
    )
    horizontal_scrollbar = tk.Scrollbar(
        editor,
        orient="horizontal",
        command=text.xview,
        relief="flat",
        bd=0,
        bg=BG_SURFACE,
        activebackground=INK_MUTED,
        troughcolor=BG_SURFACE,
        width=12,
    )
    text.grid(row=0, column=0, sticky="nsew")
    vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
    editor.grid_rowconfigure(0, weight=1)
    editor.grid_columnconfigure(0, weight=1)
    text.insert("1.0", values_to_text(_read_user_environment()))

    footer = tk.Frame(content, bg=BG_SURFACE)
    footer.pack(fill="x", pady=(18, 0))
    tk.Label(
        footer,
        text="Saved for this Windows user account",
        bg=BG_SURFACE,
        fg=INK_MUTED,
        font=("Segoe UI", 9),
    ).pack(side="left", anchor="center")

    def save() -> None:
        try:
            values = text_to_values(text.get("1.0", "end"))
        except (ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Invalid input", str(error))
            return

        missing = [name for name in REQUIRED_FIELDS if not values.get(name)]
        if missing:
            messagebox.showerror(
                "Missing values",
                "Enter values for:\n" + "\n".join(missing),
            )
            return

        try:
            _save_user_values(values)
            _broadcast_environment_change()
        except OSError as error:
            messagebox.showerror("Could not save", str(error))
            return

        messagebox.showinfo(
            "Saved",
            "Values saved for this Windows user. They will be used on the next alias request.",
        )

    def remove_saved_session() -> None:
        if not messagebox.askyesno(
            "Remove saved session?",
            "Remove all HME session values saved for this Windows user?",
        ):
            return
        try:
            failures = _remove_saved_values()
            _broadcast_environment_change()
        except OSError as error:
            messagebox.showerror("Could not remove session", str(error))
            return
        if failures:
            messagebox.showerror(
                "Could not remove all values",
                "These values could not be removed:\n" + "\n".join(failures),
            )
            return
        text.delete("1.0", "end")
        text.insert("1.0", values_to_text({}))
        messagebox.showinfo("Removed", "Saved HME session values were removed.")

    make_button(
        footer,
        "Remove session",
        background=BG_SUBTLE,
        command=remove_saved_session,
    ).pack(side="right", padx=(0, 8))
    make_button(
        footer,
        "Save session",
        background=ACCENT_LIME,
        command=save,
    ).pack(side="right")
    root.mainloop()


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