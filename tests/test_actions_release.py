"""Тестове на изчакването на физическото пускане на модификаторите преди Ctrl/Cmd+C и +V.

Бъг: при синтетично пускане на Ctrl реалното пускане идваше по-късно и попаднеше ли между
Cmd/Ctrl-down и V-down, в текста се появяваше буквата „v“ вместо paste (macOS и Windows).
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

try:
    from kirlat import actions
except Exception as e:                       # pynput иска дисплей на Linux CI
    actions, _import_error = None, e
else:
    _import_error = None

HK = {"ctrl": True, "alt": False, "shift": False, "meta": False, "key": "d"}


class FakeKeyboard:
    def __init__(self):
        self.events = []

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))


def make(held_sequence):
    """SelectionConverter с подменена проверка: held_sequence е списък от отговори
    (True=натиснат, False=пуснат, None=непроверимо); последният се повтаря."""
    conv = actions.SelectionConverter.__new__(actions.SelectionConverter)
    conv.kb = FakeKeyboard()
    conv.calls = 0

    def held(hk):
        i = min(conv.calls, len(held_sequence) - 1)
        conv.calls += 1
        return held_sequence[i]

    conv._hotkey_modifiers_held = held
    return conv


@unittest.skipIf(actions is None, f"actions deps unavailable: {_import_error}")
class WaitReleaseTests(unittest.TestCase):
    def test_returns_immediately_when_nothing_held(self):
        conv = make([False])
        self.assertTrue(conv._wait_hotkey_released(HK, timeout=1.0))
        self.assertEqual(conv.calls, 1)

    def test_waits_until_modifiers_are_released(self):
        conv = make([True, True, True, False])
        self.assertTrue(conv._wait_hotkey_released(HK, timeout=1.0))
        self.assertEqual(conv.calls, 4)

    def test_times_out_when_held_too_long(self):
        conv = make([True])
        self.assertFalse(conv._wait_hotkey_released(HK, timeout=0.05))
        self.assertGreater(conv.calls, 1)

    def test_unsupported_platform_does_not_block(self):
        conv = make([None])
        self.assertFalse(conv._wait_hotkey_released(HK, timeout=1.0))
        self.assertEqual(conv.calls, 1)

    def test_probe_failure_does_not_block(self):
        conv = make([])
        conv._hotkey_modifiers_held = mock.Mock(side_effect=RuntimeError("no Quartz"))
        self.assertFalse(conv._wait_hotkey_released(HK, timeout=1.0))


@unittest.skipIf(actions is None, f"actions deps unavailable: {_import_error}")
class ModifierProbeTests(unittest.TestCase):
    def test_mac_reads_hid_flags(self):
        fake_q = mock.Mock()
        fake_q.kCGEventSourceStateHIDSystemState = 1
        fake_q.CGEventSourceFlagsState = mock.Mock(return_value=actions._MAC_MOD_MASK["ctrl"])
        with mock.patch.dict(sys.modules, {"Quartz": fake_q}), \
                mock.patch.object(actions, "IS_MAC", True), mock.patch.object(actions, "IS_WIN", False):
            self.assertTrue(actions.SelectionConverter._hotkey_modifiers_held(HK))
            self.assertFalse(actions.SelectionConverter._hotkey_modifiers_held({**HK, "ctrl": False, "alt": True}))
            fake_q.CGEventSourceFlagsState.return_value = 0
            self.assertFalse(actions.SelectionConverter._hotkey_modifiers_held(HK))

    def test_windows_reads_async_key_state(self):
        down = {0x11}
        user32 = mock.Mock()
        user32.GetAsyncKeyState = lambda vk: 0x8000 if vk in down else 0
        fake_ctypes = mock.Mock()
        fake_ctypes.windll.user32 = user32
        with mock.patch.dict(sys.modules, {"ctypes": fake_ctypes}), \
                mock.patch.object(actions, "IS_MAC", False), mock.patch.object(actions, "IS_WIN", True):
            self.assertTrue(actions.SelectionConverter._hotkey_modifiers_held(HK))
            down.clear()
            self.assertFalse(actions.SelectionConverter._hotkey_modifiers_held(HK))
            down.add(0x5C)   # десен Win
            self.assertTrue(actions.SelectionConverter._hotkey_modifiers_held({**HK, "meta": True}))

    def test_other_platform_is_unknown(self):
        with mock.patch.object(actions, "IS_MAC", False), mock.patch.object(actions, "IS_WIN", False):
            self.assertIsNone(actions.SelectionConverter._hotkey_modifiers_held(HK))


@unittest.skipIf(actions is None, f"actions deps unavailable: {_import_error}")
class ConvertSelectionOrderTests(unittest.TestCase):
    """Синтетично пускане само ако изчакването изтече; chord-овете винаги след него."""

    def run_convert(self, released: bool):
        conv = make([not released])
        conv.get_config = lambda: {"hotkey": HK, "layout": "bds", "direction": "auto", "sound": False,
                                   "restore_clipboard": False}
        conv.notify = lambda m: None
        conv._paste_safe = staticmethod(lambda: "old")
        conv._wait_clipboard_change = lambda sentinel, timeout: "Zdrawej"
        with mock.patch.object(actions.time, "sleep"), \
                mock.patch.object(actions, "RELEASE_TIMEOUT", 0.02), \
                mock.patch.object(actions.pyperclip, "copy"), \
                mock.patch.object(actions, "convert", return_value="Здравей"):
            conv._convert_selection()
        return conv.kb.events

    def test_no_synthetic_release_when_user_let_go(self):
        events = self.run_convert(released=True)
        self.assertNotIn(("release", actions.Key.ctrl_l), events)
        self.assertEqual(events[0][0], "press")            # първото събитие е chord-ът

    def test_synthetic_release_only_after_timeout(self):
        events = self.run_convert(released=False)
        self.assertEqual(events[0], ("release", actions.Key.ctrl_l))
        self.assertEqual(events[1], ("release", actions.Key.ctrl_r))
        self.assertEqual(events[2][0], "press")


if __name__ == "__main__":
    unittest.main()
