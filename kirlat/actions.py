"""Замяна на селектирания текст: копира го (Ctrl/Cmd+C), преобразува го и го поставя (Ctrl/Cmd+V)."""
import logging
import threading
import time

import pyperclip
from pynput.keyboard import Controller, Key, KeyCode

from .config import IS_MAC, IS_WIN
from .converter import convert
from .sound import play_success

log = logging.getLogger(__name__)

SENTINEL = "⁣KirLat⁣"   # маркер, по който познаваме дали копирането е сработило
COPY_TIMEOUT = 1.0
RELEASE_TIMEOUT = 1.0   # макс. изчакване потребителят да пусне модификаторите на комбинацията

# Маски на модификаторите в CGEventFlags (macOS) и virtual-key кодове (Windows)
_MAC_MOD_MASK = {"ctrl": 0x40000, "alt": 0x80000, "shift": 0x20000, "meta": 0x100000}
_WIN_MOD_VK = {"ctrl": (0x11,), "alt": (0x12,), "shift": (0x10,), "meta": (0x5B, 0x5C)}


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

        hk = cfg.get("hotkey", {})
        self._neutralize_lonely_alt(hk)
        # Изчакваме потребителят физически да пусне Ctrl/Alt/… от комбинацията. Ако ги
        # пуснем само синтетично, реалното пускане идва по-късно – и попадне ли между
        # Cmd/Ctrl-down и V-down на нашия chord, системата „забравя“ модификатора и в текста
        # се появява буквата „v“ (или „c“) вместо paste/copy. Виждано и на macOS, и на Windows.
        if not self._wait_hotkey_released(hk):
            log.info("Hotkey modifiers still held after %.1fs – releasing them synthetically", RELEASE_TIMEOUT)
            self._release_hotkey_modifiers(hk)
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
        if cfg.get("sound", True):
            play_success()
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

    def _neutralize_lonely_alt(self, hk: dict) -> None:
        """Windows: „самотен“ Alt/Win (натиснат и пуснат без друг видим клавиш – нашият е
        погълнат от hook-а) отваря менюто/Start. Вмъкваме Ctrl, докато Alt/Win е още задържан."""
        if IS_WIN and (hk.get("alt") or hk.get("meta")):
            self.kb.press(Key.ctrl)
            self.kb.release(Key.ctrl)

    @staticmethod
    def _hotkey_modifiers_held(hk: dict):
        """Дали някой от модификаторите на комбинацията е физически натиснат.
        None – не може да се провери на тази платформа."""
        mods = [m for m in ("ctrl", "alt", "shift", "meta") if hk.get(m)]
        if IS_MAC:
            import Quartz
            flags = Quartz.CGEventSourceFlagsState(Quartz.kCGEventSourceStateHIDSystemState)
            return any(flags & _MAC_MOD_MASK[m] for m in mods)
        if IS_WIN:
            import ctypes
            user32 = ctypes.windll.user32
            return any(user32.GetAsyncKeyState(vk) & 0x8000 for m in mods for vk in _WIN_MOD_VK[m])
        return None

    def _wait_hotkey_released(self, hk: dict, timeout: float = RELEASE_TIMEOUT) -> bool:
        """Изчаква (до timeout) модификаторите на комбинацията да бъдат пуснати физически.
        True ако са пуснати; False при изтекло време или ако проверката не е възможна."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                held = self._hotkey_modifiers_held(hk)
            except Exception:
                log.debug("Modifier state check failed", exc_info=True)
                return False
            if held is None:
                return False
            if not held:
                return True
            time.sleep(0.01)
        return False

    def _release_hotkey_modifiers(self, hk: dict) -> None:
        """Пуска модификаторите на комбинацията синтетично, за да не се смесят с Ctrl+C / Ctrl+V."""
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
