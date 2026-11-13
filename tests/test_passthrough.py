"""Комбинацията се пропуска (не се прихваща) в клиенти за отдалечен достъп – там я обработва
KirLat на отдалечената машина."""
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from kirlat import foreground  # noqa: E402
from kirlat.hotkey import HotkeyListener  # noqa: E402

WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101


class Suppressed(Exception):
    pass


class FakeListener:
    def suppress_event(self):
        raise Suppressed()


class MatchTests(unittest.TestCase):
    def test_known_remote_apps(self):
        self.assertTrue(foreground.matches({"mstsc.exe"}, foreground.REMOTE_APPS))
        self.assertTrue(foreground.matches({"MSTSC.EXE"}, foreground.REMOTE_APPS))
        self.assertTrue(foreground.matches({"com.microsoft.rdc.macos", "Windows App"}, foreground.REMOTE_APPS))
        self.assertTrue(foreground.matches({"com.apple.ScreenSharing"}, foreground.REMOTE_APPS))

    def test_regular_apps_do_not_match(self):
        self.assertFalse(foreground.matches({"notepad.exe"}, foreground.REMOTE_APPS))
        self.assertFalse(foreground.matches({"com.microsoft.Word", "Microsoft Word"}, foreground.REMOTE_APPS))
        self.assertFalse(foreground.matches({"com.microsoft.rdcfoo"}, foreground.REMOTE_APPS))
        self.assertFalse(foreground.matches(set(), foreground.REMOTE_APPS))

    def test_check_respects_config(self):
        orig = foreground.foreground_app_ids
        foreground.foreground_app_ids = lambda: {"mstsc.exe"}
        try:
            self.assertTrue(foreground.make_passthrough_check({})())
            self.assertFalse(foreground.make_passthrough_check({"passthrough_remote": False})())
            foreground.foreground_app_ids = lambda: {"parsecd.exe"}
            self.assertFalse(foreground.make_passthrough_check({})())
            self.assertTrue(foreground.make_passthrough_check({"passthrough_apps": ["parsecd.exe"]})())
        finally:
            foreground.foreground_app_ids = orig


class WinPassthroughTests(unittest.TestCase):
    def make(self, remote):
        fired = []
        state = {"remote": remote}
        hl = HotkeyListener({"ctrl": True, "alt": False, "shift": False, "meta": False, "key": "w"},
                            callback=lambda: None, passthrough_check=lambda: state["remote"])
        hl._vk = 0x57
        hl._listener = FakeListener()
        hl._fire = lambda: fired.append(1)
        hl._win_mods = lambda: (True, False, False, False)
        return hl, fired, state

    def send(self, hl, msg):
        try:
            hl._win_filter(msg, SimpleNamespace(vkCode=0x57, flags=0))
        except Suppressed:
            return "suppressed"
        return "passed"

    def test_remote_app_gets_the_combo(self):
        hl, fired, _ = self.make(True)
        self.assertEqual(self.send(hl, WM_KEYDOWN), "passed")
        self.assertEqual(self.send(hl, WM_KEYDOWN), "passed")   # авто-повторение
        self.assertEqual(self.send(hl, WM_KEYUP), "passed")
        self.assertEqual(fired, [])

    def test_back_to_local_app_intercepts_again(self):
        hl, fired, state = self.make(True)
        self.send(hl, WM_KEYDOWN)
        self.send(hl, WM_KEYUP)
        state["remote"] = False
        self.assertEqual(self.send(hl, WM_KEYDOWN), "suppressed")
        self.assertEqual(self.send(hl, WM_KEYUP), "suppressed")
        self.assertEqual(fired, [1])

    def test_failing_check_falls_back_to_intercept(self):
        hl, fired, _ = self.make(True)
        hl.passthrough_check = lambda: 1 / 0
        self.assertEqual(self.send(hl, WM_KEYDOWN), "suppressed")
        self.assertEqual(fired, [1])


if __name__ == "__main__":
    unittest.main()
