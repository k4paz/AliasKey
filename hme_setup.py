"""Manual HME credential setup for Windows.

This utility opens iCloud for the user to sign in manually, then stores only
the APPLE_* values the user explicitly enters in the Windows user environment.
It does not read browser cookies, passwords, or browser storage.
"""

import os
import json
import math
import re
import sys
import uuid
import webbrowser
import winreg
import tkinter as tk
from tkinter import filedialog, messagebox


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


BG_CANVAS = "#F5F6F7"
BG_SURFACE = "#FCFCFD"
BG_SUBTLE = "#F2F1EF"
ACCENT_LIME = "#C2FA28"
TRACK_MUTED = "#E6E7E8"
INK_PRIMARY = "#111111"
INK_SECONDARY = "#6E7175"
INK_MUTED = "#9A9D9E"


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
    """Convert a browser cookie-export array into recognized APPLE_* values."""
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

    user_value = values.get("APPLE_WEBAUTH_USER", "")
    dsid_match = re.search(r"(?:^|:)d=([^:;]+)", user_value)
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
    """Accept either NAME=VALUE lines or the browser JSON cookie format."""
    stripped = raw_text.lstrip()
    if stripped.startswith("["):
        values = cookie_json_to_values(raw_text)
        values["APPLE_CLIENT_ID"] = os.environ.get(
            "APPLE_CLIENT_ID", str(uuid.uuid4())
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


def _save_user_value(name: str, value: str) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    os.environ[name] = value


def _broadcast_environment_change() -> None:
    try:
        import ctypes

        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF,
            0x001A,
            0,
            "Environment",
            0x0002,
            5000,
            None,
        )
    except Exception:
        pass


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


def main() -> None:
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
        width = max(1, event.width - 48)
        height = max(1, event.height - 48)
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
        card_canvas.itemconfigure(card_window, width=width, height=height)

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
    text.insert("1.0", values_to_text({}))

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
            explanation = "Enter values for:\n" + "\n".join(missing)
            messagebox.showerror(
                "Missing values",
                explanation,
            )
            return

        try:
            for name, value in values.items():
                _save_user_value(name, value)
            _broadcast_environment_change()
        except OSError as error:
            messagebox.showerror("Could not save", str(error))
            return

        messagebox.showinfo(
            "Saved",
            "Values saved for your Windows user account. Start a new HME hotkey process to load them.",
        )

    make_button(
        footer,
        "Save session",
        background=ACCENT_LIME,
        command=save,
    ).pack(side="right")
    root.mainloop()


if __name__ == "__main__":
    main()