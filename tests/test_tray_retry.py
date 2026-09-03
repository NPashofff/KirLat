"""Тестове на логиката за рестарт на слушателя в трея (без реална икона и без реален hook)."""
import os
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

try:
    from kirlat import tray as tray_mod
except Exception as e:                       # pystray/pynput искат дисплей на Linux CI
    tray_mod, _import_error = None, e
else:
    _import_error = None


@unittest.skipIf(tray_mod is None, f"tray deps unavailable: {_import_error}")
class RetryListenerTests(unittest.TestCase):
    def make(self, listener_ok=True, alive=True):
        app = tray_mod.TrayApp.__new__(tray_mod.TrayApp)
        app.cfg = {"hotkey": {"ctrl": True, "key": "w"}}
        app._stop = threading.Event()
        app._init_listener_state()
        app.now = 1000.0
        app._clock = lambda: app.now
        app.icon = SimpleNamespace(update_menu=lambda: None)
        app.notices = []
        app.notify = app.notices.append
        app.starts = []
        app.next_start_ok = True

        def fake_start(notify_failure=True):
            app.starts.append(notify_failure)
            app.listener_ok = app.next_start_ok
            app.listener = SimpleNamespace(running=app.next_start_ok, stop=lambda: None)

        app.start_listener = fake_start
        app.listener_ok = listener_ok
        app.listener = SimpleNamespace(running=alive, stop=lambda: None)
        return app

    def tick(self, app, seconds=3):
        app.now += seconds
        app._retry_listener_if_permitted()

    def test_healthy_listener_is_left_alone(self):
        app = self.make()
        self.tick(app)
        self.assertEqual(app.starts, [])

    def test_dead_thread_is_restarted_and_announced(self):
        app = self.make()
        app.listener.running = False
        with mock.patch.object(tray_mod, "IS_MAC", False):
            self.tick(app)
        self.assertEqual(app.starts, [False])          # без известие за неуспех
        self.assertTrue(app.listener_ok)
        self.assertEqual(len(app.notices), 1)
        self.assertIn("активна", app.notices[0])

    def test_failed_start_backs_off_exponentially(self):
        app = self.make(listener_ok=False)
        app.next_start_ok = False
        with mock.patch.object(tray_mod, "IS_MAC", False):
            self.tick(app)                         # опит 1, следващият след 3 s
            self.assertEqual(len(app.starts), 1)
            self.tick(app, 2)
            self.assertEqual(len(app.starts), 1)   # още е рано
            self.tick(app, 1)
            self.assertEqual(len(app.starts), 2)   # следващият след 6 s
            self.tick(app, 5)
            self.assertEqual(len(app.starts), 2)
            self.tick(app, 1)
            self.assertEqual(len(app.starts), 3)
            for _ in range(20):
                self.tick(app, 400)
            self.assertEqual(app._retry_delay, tray_mod.TrayApp.RETRY_DELAY_MAX)
            self.assertEqual(app.notices, [])      # неуспехите не спамят
            app.next_start_ok = True
            self.tick(app, 400)
        self.assertTrue(app.listener_ok)
        self.assertEqual(app._retry_delay, tray_mod.TrayApp.RETRY_DELAY_MIN)
        self.assertEqual(len(app.notices), 1)

    def test_mac_waits_for_accessibility(self):
        app = self.make(listener_ok=False)
        with mock.patch.object(tray_mod, "IS_MAC", True), \
                mock.patch.object(tray_mod, "mac_accessibility_trusted", lambda prompt: False):
            self.tick(app)
            self.assertEqual(app.starts, [])
        with mock.patch.object(tray_mod, "IS_MAC", True), \
                mock.patch.object(tray_mod, "mac_accessibility_trusted", lambda prompt: True):
            self.tick(app)
            self.assertEqual(app.starts, [False])
        self.assertTrue(app.listener_ok)

    def test_no_restart_after_quit(self):
        app = self.make()
        app._stop.set()
        app.listener.running = False
        with mock.patch.object(tray_mod, "IS_MAC", False):
            self.tick(app)
        self.assertEqual(app.starts, [])


if __name__ == "__main__":
    unittest.main()
