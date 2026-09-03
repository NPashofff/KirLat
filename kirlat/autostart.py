"""Автоматично стартиране при вход в системата."""
import os
import plistlib
import subprocess

from .config import APP_NAME, IS_MAC, IS_WIN
from .platform_utils import app_command

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
MAC_LABEL = "com.kirlat.app"


def _mac_plist_path() -> str:
    return os.path.expanduser(f"~/Library/LaunchAgents/{MAC_LABEL}.plist")


def _linux_desktop_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "autostart", f"{APP_NAME}.desktop")


def is_enabled() -> bool:
    if IS_WIN:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
                winreg.QueryValueEx(k, APP_NAME)
                return True
        except OSError:
            return False
    if IS_MAC:
        return os.path.exists(_mac_plist_path())
    return os.path.exists(_linux_desktop_path())


def set_enabled(flag: bool) -> None:
    if IS_WIN:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if flag:
                cmd = " ".join(f'"{p}"' for p in app_command())
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return

    if IS_MAC:
        path = _mac_plist_path()
        if flag:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            plist = {
                "Label": MAC_LABEL,
                "ProgramArguments": app_command(),
                "RunAtLoad": True,
                "KeepAlive": False,
                "ProcessType": "Interactive",
            }
            with open(path, "wb") as f:
                plistlib.dump(plist, f)
            subprocess.run(["launchctl", "load", "-w", path], capture_output=True)
        else:
            if os.path.exists(path):
                subprocess.run(["launchctl", "unload", "-w", path], capture_output=True)
                os.remove(path)
        return

    path = _linux_desktop_path()
    if flag:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cmd = " ".join(f'"{p}"' for p in app_command())
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"[Desktop Entry]\nType=Application\nName={APP_NAME}\nExec={cmd}\nX-GNOME-Autostart-enabled=true\n")
    elif os.path.exists(path):
        os.remove(path)
