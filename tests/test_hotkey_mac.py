"""Тестове на macOS intercept логиката (без реален CGEventTap – Quartz е подменен с фалшив модул)."""
import os
import sys
import types
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from kirlat.hotkey import HotkeyListener  # noqa: E402

KEY_DOWN, KEY_UP, FLAGS_CHANGED = 10, 11, 12
TAP_DISABLED_TIMEOUT, TAP_DISABLED_USER = 0xFFFFFFFE, 0xFFFFFFFF
SHIFT, CTRL, ALT, CMD = 0x20000, 0x40000, 0x80000, 0x100000
KEYCODE_W, KEYCODE_C = 13, 8


def _fake_quartz(enabled_calls):
    q = types.ModuleType("Quartz")
    q.kCGEventKeyDown, q.kCGEventKeyUp, q.kCGEventFlagsChanged = KEY_DOWN, KEY_UP, FLAGS_CHANGED
    q.kCGEventTapDisabledByTimeout, q.kCGEventTapDisabledByUserInput = TAP_DISABLED_TIMEOUT, TAP_DISABLED_USER
    q.kCGKeyboardEventKeycode = 9
    q.kCGEventFlagMaskShift, q.kCGEventFlagMaskControl = SHIFT, CTRL
    q.kCGEventFlagMaskAlternate, q.kCGEventFlagMaskCommand = ALT, CMD
    q.CGEventGetIntegerValueField = lambda event, field: event.keycode
    q.CGEventGetFlags = lambda event: event.flags
    q.CGEventTapEnable = lambda tap, enable: enabled_calls.append((tap, enable))
    return q


class MacInterceptTests(unittest.TestCase):
    def setUp(self):
        self.enabled = []
        self._saved = sys.modules.get("Quartz")
        sys.modules["Quartz"] = _fake_quartz(self.enabled)

    def tearDown(self):
        if self._saved is not None:
            sys.modules["Quartz"] = self._saved
        else:
            sys.modules.pop("Quartz", None)

    def make(self):
        fired = []
        hl = HotkeyListener({"ctrl": True, "alt": False, "shift": False, "meta": False, "key": "w"},
                            callback=lambda: None)
        hl._keycode = KEYCODE_W
        hl._fire = lambda: fired.append(1)
        return hl, fired

    @staticmethod
    def send(hl, event_type, keycode=KEYCODE_W, flags=CTRL):
        ev = SimpleNamespace(keycode=keycode, flags=flags)
        out = hl._mac_intercept(event_type, ev)
        return "suppressed" if out is None else "passed"

    def test_ctrl_w_fires_and_is_suppressed(self):
        hl, fired = self.make()
        self.assertEqual(self.send(hl, KEY_DOWN), "suppressed")
        self.assertEqual(len(fired), 1)
        # авто-повторение при задържан клавиш: поглъща се, но не се задейства пак
        self.assertEqual(self.send(hl, KEY_DOWN), "suppressed")
        self.assertEqual(len(fired), 1)
        self.assertEqual(self.send(hl, KEY_UP), "suppressed")
        self.assertEqual(self.send(hl, KEY_DOWN), "suppressed")
        self.assertEqual(len(fired), 2)

    def test_plain_w_passes(self):
        hl, fired = self.make()
        self.assertEqual(self.send(hl, KEY_DOWN, flags=0), "passed")
        self.assertEqual(self.send(hl, KEY_UP, flags=0), "passed")
        self.assertEqual(fired, [])

    def test_extra_modifier_passes(self):
        hl, fired = self.make()
        self.assertEqual(self.send(hl, KEY_DOWN, flags=CTRL | SHIFT), "passed")   # Ctrl+Shift+W
        self.assertEqual(self.send(hl, KEY_DOWN, flags=CMD), "passed")            # Cmd+W – затваря таб
        self.assertEqual(fired, [])

    def test_other_key_and_other_event_types_pass(self):
        hl, fired = self.make()
        self.assertEqual(self.send(hl, KEY_DOWN, keycode=KEYCODE_C), "passed")
        self.assertEqual(self.send(hl, FLAGS_CHANGED), "passed")
        self.assertEqual(fired, [])

    def test_busy_swallows_without_firing(self):
        hl, fired = self.make()
        hl.busy_check = lambda: True
        self.assertEqual(self.send(hl, KEY_DOWN), "suppressed")
        self.assertEqual(self.send(hl, KEY_UP), "suppressed")
        self.assertEqual(fired, [])

    def test_key_up_without_swallowed_down_passes(self):
        hl, fired = self.make()
        self.assertEqual(self.send(hl, KEY_UP), "passed")

    def test_disabled_tap_is_re_enabled(self):
        hl, fired = self.make()
        hl._listener = SimpleNamespace(tap="TAP")
        self.assertEqual(self.send(hl, TAP_DISABLED_TIMEOUT), "passed")
        self.assertEqual(self.send(hl, TAP_DISABLED_USER), "passed")
        self.assertEqual(self.enabled, [("TAP", True), ("TAP", True)])
        self.assertEqual(fired, [])

    def test_disabled_tap_without_reference_is_harmless(self):
        hl, fired = self.make()
        self.assertEqual(self.send(hl, TAP_DISABLED_TIMEOUT), "passed")     # _listener е None
        hl._listener = SimpleNamespace(tap=None)                             # tap не е създаден
        self.assertEqual(self.send(hl, TAP_DISABLED_TIMEOUT), "passed")
        self.assertEqual(self.enabled, [])

    @unittest.skipUnless(sys.platform == "darwin", "pynput/Quartz only on macOS")
    def test_tap_listener_overrides_real_pynput_hook(self):
        from kirlat.hotkey import _mac_listener_class
        cls = _mac_listener_class()
        base = cls.__mro__[1]
        # ако pynput преименува метода, override-ът става мъртъв код – тестът го хваща
        self.assertTrue(hasattr(base, "_create_event_tap"))
        self.assertIsNot(cls._create_event_tap, base._create_event_tap)


if __name__ == "__main__":
    unittest.main()
