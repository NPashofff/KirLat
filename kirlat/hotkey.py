"""Глобална клавишна комбинация, независима от активната клавиатурна подредба.

Windows: low-level keyboard hook (pynput) + филтър по virtual-key код; комбинацията се
„поглъща“, така че приложението под курсора не я получава (напр. Ctrl+W не затваря таб).
macOS: CGEventTap (pynput darwin_intercept) + филтър по хардуерен keycode.
"""
import logging
import threading

from .config import IS_MAC, IS_WIN
from .layouts import MAC_KEYCODE, WIN_VK

log = logging.getLogger(__name__)


def _mac_listener_class():
    """pynput Listener, който пази CGEventTap-а си (pynput го държи само като локална
    променлива), за да можем да го включим отново, ако macOS го спре. Ако бъдеща версия
    на pynput преименува _create_event_tap, методът просто не се вика и tap остава None –
    комбинацията работи, губи се само повторното включване."""
    from pynput import keyboard

    class TapListener(keyboard.Listener):
        tap = None

        def _create_event_tap(self):
            self.tap = super()._create_event_tap()
            return self.tap

    return TapListener


class HotkeyListener:
    def __init__(self, hotkey: dict, callback, busy_check=None):
        self.hotkey = hotkey
        self.callback = callback
        self.busy_check = busy_check or (lambda: False)
        self._key = str(hotkey.get("key", "w")).lower()
        self._mods = (
            bool(hotkey.get("ctrl")),
            bool(hotkey.get("alt")),
            bool(hotkey.get("shift")),
            bool(hotkey.get("meta")),
        )
        self._listener = None
        self._armed = True          # False докато клавишът е задържан (без авто-повторение)
        self._swallow_up = False    # погълни и key-up, ако key-down е бил погълнат

    # ------------------------------------------------------------------ API
    def start(self) -> None:
        from pynput import keyboard

        if IS_WIN:
            self._vk = WIN_VK[self._key]
            self._listener = keyboard.Listener(win32_event_filter=self._win_filter)
        elif IS_MAC:
            self._keycode = MAC_KEYCODE[self._key]
            self._listener = _mac_listener_class()(darwin_intercept=self._mac_intercept)
        else:
            self._listener = keyboard.GlobalHotKeys({self._linux_combo(): self._fire})
        self._listener.daemon = True
        if IS_MAC:
            self._log_mac_permissions()
        self._listener.start()
        # На macOS без разрешение Accessibility event tap-ът не може да се създаде: pynput
        # маркира listener-а като „готов“ и нишката просто приключва (running остава True!).
        # Затова проверяваме дали нишката е жива, не флага running.
        import time
        try:
            self._listener.wait()
        except Exception:
            pass
        time.sleep(0.2)
        if not self._listener.is_alive():
            self._listener = None
            raise RuntimeError(
                "слушателят на клавиатурата не стартира"
                + (" – липсва разрешение Accessibility / Input Monitoring" if IS_MAC else "")
            )
        log.info("Hotkey listener started: %s", self.hotkey)

    @property
    def running(self) -> bool:
        return self._listener is not None and self._listener.is_alive()

    @staticmethod
    def _log_mac_permissions() -> None:
        try:
            import Quartz
            from ApplicationServices import AXIsProcessTrusted
            log.info(
                "macOS permissions: accessibility=%s listen=%s post=%s",
                bool(AXIsProcessTrusted()),
                bool(Quartz.CGPreflightListenEventAccess()) if hasattr(Quartz, "CGPreflightListenEventAccess") else "?",
                bool(Quartz.CGPreflightPostEventAccess()) if hasattr(Quartz, "CGPreflightPostEventAccess") else "?",
            )
        except Exception as e:
            log.info("macOS permissions check failed: %s", e)

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    # -------------------------------------------------------------- helpers
    def _fire(self) -> None:
        log.info("Hotkey pressed")
        threading.Thread(target=self._safe_callback, daemon=True).start()

    def _safe_callback(self) -> None:
        try:
            self.callback()
        except Exception:
            log.exception("Hotkey callback failed")

    def _linux_combo(self) -> str:
        ctrl, alt, shift, meta = self._mods
        parts = []
        if ctrl:
            parts.append("<ctrl>")
        if alt:
            parts.append("<alt>")
        if shift:
            parts.append("<shift>")
        if meta:
            parts.append("<cmd>")
        key = self._key
        parts.append(f"<{key}>" if len(key) > 1 else key)
        return "+".join(parts)

    # -------------------------------------------------------------- Windows
    @staticmethod
    def _win_mods():
        import ctypes
        user32 = ctypes.windll.user32

        def down(vk):
            return bool(user32.GetAsyncKeyState(vk) & 0x8000)

        return (down(0x11), down(0x12), down(0x10), down(0x5B) or down(0x5C))

    def _win_filter(self, msg, data):
        if data.vkCode != self._vk:
            return
        if data.flags & 0x10:      # LLKHF_INJECTED – наши собствени симулирани клавиши
            return
        if msg in (0x0100, 0x0104):            # WM_KEYDOWN / WM_SYSKEYDOWN
            if self._win_mods() != self._mods:
                return
            if self._armed and not self.busy_check():
                self._armed = False
                self._fire()
            self._swallow_up = True
            self._listener.suppress_event()
        elif msg in (0x0101, 0x0105):          # WM_KEYUP / WM_SYSKEYUP
            self._armed = True
            if self._swallow_up:
                self._swallow_up = False
                self._listener.suppress_event()

    # ---------------------------------------------------------------- macOS
    def _mac_intercept(self, event_type, event):
        import Quartz

        if event_type in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            # macOS спира tap-а, ако callback-ът се забави; без включване комбинацията умира тихо.
            log.warning("macOS disabled the event tap (type %s) – re-enabling", event_type)
            tap = getattr(self._listener, "tap", None)
            if tap is not None:
                Quartz.CGEventTapEnable(tap, True)
            return event
        if event_type not in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
            return event
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        if keycode != self._keycode:
            return event
        if event_type == Quartz.kCGEventKeyDown:
            flags = Quartz.CGEventGetFlags(event)
            mods = (
                bool(flags & Quartz.kCGEventFlagMaskControl),
                bool(flags & Quartz.kCGEventFlagMaskAlternate),
                bool(flags & Quartz.kCGEventFlagMaskShift),
                bool(flags & Quartz.kCGEventFlagMaskCommand),
            )
            if mods != self._mods:
                return event
            if self._armed and not self.busy_check():
                self._armed = False
                self._fire()
            self._swallow_up = True
            return None
        self._armed = True
        if self._swallow_up:
            self._swallow_up = False
            return None
        return event
