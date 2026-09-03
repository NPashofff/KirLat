"""Тестове на логиката на Windows филтъра за клавишни комбинации (без реален hook)."""
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from kirlat.hotkey import HotkeyListener  # noqa: E402

WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101


class Suppressed(Exception):
    pass


class FakeListener:
    def suppress_event(self):
        raise Suppressed()


class WinFilterTests(unittest.TestCase):
    def make(self, mods_down):
        fired = []
        hl = HotkeyListener({"ctrl": True, "alt": False, "shift": False, "meta": False, "key": "w"},
                            callback=lambda: None)
        hl._vk = 0x57
        hl._listener = FakeListener()
        hl._fire = lambda: fired.append(1)
        hl._win_mods = lambda: mods_down
        return hl, fired

    def send(self, hl, msg, vk, injected=False):
        data = SimpleNamespace(vkCode=vk, flags=0x10 if injected else 0)
        try:
            hl._win_filter(msg, data)
        except Suppressed:
            return "suppressed"
        return "passed"

    def test_ctrl_w_fires_and_is_suppressed(self):
        hl, fired = self.make((True, False, False, False))
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x57), "suppressed")
        self.assertEqual(len(fired), 1)
        # авто-повторение при задържан клавиш: поглъща се, но не се задейства пак
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x57), "suppressed")
        self.assertEqual(len(fired), 1)
        self.assertEqual(self.send(hl, WM_KEYUP, 0x57), "suppressed")
        # следващо натискане – задейства се отново
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x57), "suppressed")
        self.assertEqual(len(fired), 2)

    def test_plain_w_passes(self):
        hl, fired = self.make((False, False, False, False))
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x57), "passed")
        self.assertEqual(self.send(hl, WM_KEYUP, 0x57), "passed")
        self.assertEqual(fired, [])

    def test_extra_modifier_passes(self):
        hl, fired = self.make((True, False, True, False))   # Ctrl+Shift+W
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x57), "passed")
        self.assertEqual(fired, [])

    def test_other_key_and_injected_pass(self):
        hl, fired = self.make((True, False, False, False))
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x43), "passed")
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x57, injected=True), "passed")
        self.assertEqual(fired, [])

    def test_busy_swallows_without_firing(self):
        hl, fired = self.make((True, False, False, False))
        hl.busy_check = lambda: True
        self.assertEqual(self.send(hl, WM_KEYDOWN, 0x57), "suppressed")
        self.assertEqual(fired, [])


if __name__ == "__main__":
    unittest.main()
