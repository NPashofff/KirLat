"""Замяна на селектирания текст: копира го (Ctrl/Cmd+C), преобразува го и го поставя (Ctrl/Cmd+V)."""
import logging
import threading
import time

import pyperclip
from pynput.keyboard import Controller, Key, KeyCode

from .config import IS_MAC, IS_WIN
from .converter import convert

log = logging.getLogger(__name__)

SENTINEL = "⁣KirLat⁣"   # маркер, по който познаваме дали копирането е сработило
COPY_TIMEOUT = 1.0


def _vk_key(char: str):
    """Клавиш по физическа позиция (работи и при активна кирилска подредба)."""
    if IS_MAC:
        return KeyCode.from_vk({"c": 8, "v": 9}[char])
    if IS_WIN:
        return KeyCode.from_vk(ord(char.upper()))
    return char


class SelectionConverter:
    def __init__(self, get_config, notify=None):
        self.get_config = get_config
        self.notify = notify or (lambda msg: None)
        self._lock = threading.Lock()
        self.kb = Controller()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    # ------------------------------------------------------------------ API
    def run(self) -> None:
        if not self._lock.acquire(blocking=False):
            return
        try:
            self._convert_selection()
        except Exception as e:
            log.exception("Conversion failed")
            self.notify(f"Грешка при преобразуване: {e}")
        finally:
            self._lock.release()

    # -------------------------------------------------------------- internal
    def _convert_selection(self) -> None:
        cfg = self.get_config()
        old_clip = self._paste_safe()

        self._release_hotkey_modifiers(cfg.get("hotkey", {}))
        time.sleep(0.05)

        pyperclip.copy(SENTINEL)
        self._chord(_vk_key("c"))
        text = self._wait_clipboard_change(SENTINEL, COPY_TIMEOUT)

        if not text:
            log.info("Nothing selected / nothing copied")
            self._restore(old_clip, cfg)
            return

        new_text = convert(text, cfg.get("layout"), cfg.get("direction", "auto"))
        if new_text == text:
            self._restore(old_clip, cfg)
            return

        pyperclip.copy(new_text)
        time.sleep(0.05)
        self._chord(_vk_key("v"))
        time.sleep(0.3)
        self._restore(old_clip, cfg)
        log.info("Converted %d chars", len(text))

    def _chord(self, key) -> None:
        mod = Key.cmd if IS_MAC else Key.ctrl
        self.kb.press(mod)
        time.sleep(0.02)
        self.kb.press(key)
        time.sleep(0.02)
        self.kb.release(key)
        time.sleep(0.02)
        self.kb.release(mod)

    def _release_hotkey_modifiers(self, hk: dict) -> None:
        """Пуска модификаторите на комбинацията, за да не се смесят с Ctrl+C / Ctrl+V."""
        if IS_WIN and (hk.get("alt") or hk.get("meta")):
            # „самотен“ Alt/Win отваря меню/Start – вмъкваме Ctrl, за да не е самотен
            self.kb.press(Key.ctrl)
            self.kb.release(Key.ctrl)
        keys = []
        if hk.get("ctrl"):
            keys += [Key.ctrl_l, Key.ctrl_r]
        if hk.get("alt"):
            keys += [Key.alt_l, Key.alt_r]
        if hk.get("shift"):
            keys += [Key.shift_l, Key.shift_r]
        if hk.get("meta"):
            keys += [Key.cmd_l, Key.cmd_r]
        for k in keys:
            try:
                self.kb.release(k)
            except Exception:
                pass

    @staticmethod
    def _paste_safe():
        try:
            return pyperclip.paste()
        except Exception:
            return None

    def _wait_clipboard_change(self, sentinel: str, timeout: float):
        end = time.time() + timeout
        while time.time() < end:
            val = self._paste_safe()
            if val is not None and val != sentinel:
                return val
            time.sleep(0.02)
        return None

    @staticmethod
    def _restore(old_clip, cfg) -> None:
        if not cfg.get("restore_clipboard", True):
            return
        try:
            pyperclip.copy(old_clip or "")
        except Exception:
            pass
