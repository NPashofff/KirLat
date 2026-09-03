"""Икона в системния трей / лентата с менюта."""
import logging
import os
import subprocess
import threading
import time

import pystray

from . import autostart, config
from .actions import SelectionConverter
from .hotkey import HotkeyListener
from .config import IS_MAC
from .icon import make_icon_image, make_mac_template_icon
from .platform_utils import app_command, mac_accessibility_trusted

log = logging.getLogger(__name__)


class TrayApp:
    def __init__(self):
        self.cfg = config.load()
        self.converter = SelectionConverter(lambda: self.cfg, notify=self.notify)
        self.listener = None
        self._settings_proc = None
        self._stop = threading.Event()
        self.icon = pystray.Icon("KirLat", make_icon_image(64), self._title(), menu=self._menu())

    # ------------------------------------------------------------------ UI
    def _title(self) -> str:
        return f"KirLat – {config.hotkey_label(self.cfg['hotkey'])}"

    def _menu(self):
        return pystray.Menu(
            pystray.MenuItem("Настройки…", self.open_settings, default=True),
            pystray.MenuItem("Преобразувай селекцията", self.convert_now),
            pystray.MenuItem(
                "Стартирай при вход в системата",
                self.toggle_autostart,
                checked=lambda item: autostart.is_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Изход", self.quit),
        )

    def notify(self, message: str) -> None:
        try:
            self.icon.notify(message, "KirLat")
        except Exception:
            log.info("notify: %s", message)

    # --------------------------------------------------------------- actions
    def run(self) -> None:
        self.icon.run(setup=self._setup)

    def _setup(self, icon) -> None:
        icon.visible = True
        self._apply_mac_template_icon()
        if not mac_accessibility_trusted(prompt=True):
            self.notify("Дайте разрешение за Accessibility в System Settings → Privacy & Security.")
        self.start_listener()
        threading.Thread(target=self._watch_config, daemon=True).start()

    def _apply_mac_template_icon(self) -> None:
        """macOS: заменя иконата с монохромна Retina „template“ икона (pystray подава 1x цветна)."""
        if not IS_MAC:
            return
        try:
            import io

            import AppKit
            import Foundation

            buf = io.BytesIO()
            make_mac_template_icon(44).save(buf, "png")
            data = Foundation.NSData.dataWithBytes_length_(buf.getvalue(), len(buf.getvalue()))

            def apply():
                try:
                    ns = AppKit.NSImage.alloc().initWithData_(data)
                    ns.setSize_((22, 22))
                    ns.setTemplate_(True)
                    self.icon._icon_image = ns
                    self.icon._status_item.button().setImage_(ns)
                except Exception:
                    log.exception("Mac template icon failed")

            Foundation.NSOperationQueue.mainQueue().addOperationWithBlock_(apply)
        except Exception:
            log.exception("Mac template icon setup failed")

    def start_listener(self) -> None:
        if self.listener is not None:
            self.listener.stop()
        self.listener = HotkeyListener(
            self.cfg["hotkey"], self.converter.run, busy_check=lambda: self.converter.busy
        )
        try:
            self.listener.start()
        except Exception as e:
            log.exception("Cannot start hotkey listener")
            self.notify(f"Клавишната комбинация не може да бъде регистрирана: {e}")

    def reload(self) -> None:
        self.cfg = config.load()
        self.icon.title = self._title()
        self.start_listener()
        self.notify(f"Настройките са приложени. Комбинация: {config.hotkey_label(self.cfg['hotkey'])}")

    def _watch_config(self) -> None:
        """Презарежда настройките, когато файлът бъде променен (от прозореца за настройки)."""
        path = config.config_path()
        last = os.path.getmtime(path) if os.path.exists(path) else None
        while not self._stop.is_set():
            time.sleep(1.0)
            try:
                cur = os.path.getmtime(path) if os.path.exists(path) else None
            except OSError:
                cur = None
            if cur != last:
                last = cur
                try:
                    self.reload()
                except Exception:
                    log.exception("Reload failed")

    def open_settings(self, *_) -> None:
        if self._settings_proc is not None and self._settings_proc.poll() is None:
            return
        try:
            self._settings_proc = subprocess.Popen(app_command() + ["--settings"])
        except Exception as e:
            log.exception("Cannot open settings")
            self.notify(f"Прозорецът с настройки не може да се отвори: {e}")

    def convert_now(self, *_) -> None:
        def go():
            time.sleep(0.4)   # изчакай менюто да се затвори и фокусът да се върне
            self.converter.run()
        threading.Thread(target=go, daemon=True).start()

    def toggle_autostart(self, *_) -> None:
        try:
            autostart.set_enabled(not autostart.is_enabled())
        except Exception as e:
            log.exception("Autostart toggle failed")
            self.notify(f"Автостартът не може да бъде променен: {e}")

    def quit(self, *_) -> None:
        self._stop.set()
        if self.listener is not None:
            self.listener.stop()
        self.icon.stop()
