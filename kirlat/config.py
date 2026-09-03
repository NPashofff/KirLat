import copy
import json
import os
import sys

APP_NAME = "KirLat"
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

DEFAULTS = {
    "hotkey": {"ctrl": True, "alt": False, "shift": False, "meta": False, "key": "w"},
    "layout": "phonetic_traditional",
    "direction": "auto",          # auto | to_bg | to_en
    "restore_clipboard": True,
    "sound": True,
}


def config_dir() -> str:
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif IS_MAC:
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP_NAME)


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def log_path() -> str:
    return os.path.join(config_dir(), "kirlat.log")


def _merge(defaults, data):
    out = copy.deepcopy(defaults)
    if not isinstance(data, dict):
        return out
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load() -> dict:
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            return _merge(DEFAULTS, json.load(f))
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULTS)


def save(cfg: dict) -> None:
    os.makedirs(config_dir(), exist_ok=True)
    tmp = config_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config_path())


def hotkey_label(hk: dict) -> str:
    parts = []
    if hk.get("ctrl"):
        parts.append("Ctrl")
    if hk.get("alt"):
        parts.append("Option" if IS_MAC else "Alt")
    if hk.get("shift"):
        parts.append("Shift")
    if hk.get("meta"):
        parts.append("Cmd" if IS_MAC else "Win")
    key = str(hk.get("key", "w"))
    parts.append("Space" if key == "space" else key.upper())
    return "+".join(parts)
