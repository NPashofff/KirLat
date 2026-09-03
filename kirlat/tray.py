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
from .icon import make_icon_image
from .platform_utils import app_command, mac_accessibility_trusted

log = logging.getLogger(__name__)


class TrayApp:
    def __init__(self):
        self.cfg = config.load()
        self.converter = SelectionConverter(lambda: self.cfg, notify=self.notify)
        self.listener = None
        self.listener_ok = False
        self._settings_proc = None
        self._stop = threading.Event()
        self._init_listener_state()
        self.icon = pystray.Icon("KirLat", make_icon_image(64), self._title(), menu=self._menu())

    # ------------------------------------------------------------------ UI
    def _title(self) -> str:
        return f"KirLat – {config.hotkey_label(self.cfg['hotkey'])}"

    def _status_text(self, *_) -> str:
        label = config.hotkey_label(self.cfg["hotkey"])
        if self.listener_ok:
            return f"{label}: активна"
        return f"{label}: НЕ Е АКТИВНА" + (" – няма разрешение" if IS_MAC else "")

    def _menu(self):
        items = [
            pystray.MenuItem(self._status_text, None, enabled=False),
        ]
        if IS_MAC:
            items.append(pystray.MenuItem("Отвори разрешенията на macOS…", self.open_mac_permissions))
        items.append(pystray.Menu.SEPARATOR)
        return pystray.Menu(
            *items,
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
        if IS_MAC:
            self._mac_show_on_main_thread()
        else:
            icon.visible = True
        if not mac_accessibility_trusted(prompt=True):
            self.notify("Дайте разрешение за Accessibility в System Settings → Privacy & Security.")
        self.start_listener()
        threading.Thread(target=self._watch_config, daemon=True).start()

    def _mac_show_on_main_thread(self) -> None:
        """macOS: показва елемента в лентата и слага монохромна „template“ икона.

        Всичко върви в главната нишка (AppKit не е thread-safe; pystray вика setup от помощна
        нишка). Иконата се рисува с родния системен шрифт през AppKit, така че кирилицата е
        гарантирана и е Retina. Ако нещо се провали, елементът показва текст „КЛ“, за да не е
        никога с нулева ширина (невидим).
        """
        import Foundation

        def apply():
            try:
                self.icon.visible = True
            except Exception:
                log.exception("icon.visible failed")
            try:
                self._mac_set_template_icon()
            except Exception:
                log.exception("Mac template icon failed; falling back to text title")
                self._mac_set_text_title()

        try:
            Foundation.NSOperationQueue.mainQueue().addOperationWithBlock_(apply)
        except Exception:
            log.exception("Main-queue dispatch failed; showing from setup thread")
            apply()

    def _mac_set_template_icon(self) -> None:
        import AppKit
        import Foundation

        button = self.icon._status_item.button()
        size = 22.0
        img = AppKit.NSImage.alloc().initWithSize_((size, size))
        img.lockFocus()
        try:
            attrs = {
                AppKit.NSFontAttributeName: AppKit.NSFont.boldSystemFontOfSize_(12.5),
                AppKit.NSForegroundColorAttributeName: AppKit.NSColor.blackColor(),
            }
            text = Foundation.NSAttributedString.alloc().initWithString_attributes_("КЛ", attrs)
            w, h = text.size().width, text.size().height
            text.drawAtPoint_(((size - w) / 2.0, (size - h) / 2.0))
        finally:
            img.unlockFocus()
        img.setTemplate_(True)
        self.icon._icon_image = img
        button.setImage_(img)
        button.setTitle_("")
        button.setImagePosition_(AppKit.NSImageOnly)
        button.setHidden_(False)
        log.info("macOS menu bar icon applied (template image)")

    def _mac_set_text_title(self) -> None:
        try:
            import AppKit
            button = self.icon._status_item.button()
            button.setImage_(None)
            button.setTitle_("КЛ")
            button.setImagePosition_(AppKit.NSNoImage)
            button.setHidden_(False)
            log.info("macOS menu bar icon applied (text title)")
        except Exception:
            log.exception("Mac text title failed")

    RETRY_DELAY_MIN = 3.0       # секунди между опитите за (ре)стартиране на слушателя
    RETRY_DELAY_MAX = 300.0

    def _init_listener_state(self) -> None:
        self.listener = None
        self.listener_ok = False
        self._next_listener_retry = 0.0
        self._retry_delay = self.RETRY_DELAY_MIN
        self._clock = time.time

    def start_listener(self, notify_failure: bool = True) -> None:
        if self.listener is not None:
            self.listener.stop()
        self.listener = HotkeyListener(
            self.cfg["hotkey"], self.converter.run, busy_check=lambda: self.converter.busy
        )
        try:
            self.listener.start()
            self.listener_ok = True
        except Exception as e:
            self.listener_ok = False
            log.error("Cannot start hotkey listener: %s", e)
            if notify_failure:
                self.notify(f"Клавишната комбинация не е активна: {e}")
        try:
            self.icon.update_menu()
        except Exception:
            pass

    def open_mac_permissions(self, *_) -> None:
        try:
            subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
        except Exception:
            log.exception("Cannot open System Settings")

    def _retry_listener_if_permitted(self) -> None:
        """Активира комбинацията без рестарт на приложението: ако слушателят не е стартирал
        (на macOS – щом бъде дадено разрешението Accessibility) или нишката му е умряла.
        Известие има само при успех; между неуспешните опити изчакването расте до 5 min."""
        if self._stop.is_set():
            return
        if self.listener_ok and self.listener is not None and not self.listener.running:
            log.warning("Hotkey listener thread died – will restart")
            self.listener_ok = False
            try:
                self.icon.update_menu()
            except Exception:
                pass
        if self.listener_ok or self._clock() < self._next_listener_retry:
            return
        if IS_MAC and not mac_accessibility_trusted(prompt=False):
            return
        log.info("Retrying hotkey listener")
        self.start_listener(notify_failure=False)
        if self.listener_ok:
            self._retry_delay = self.RETRY_DELAY_MIN
            self.notify(f"Комбинацията {config.hotkey_label(self.cfg['hotkey'])} е активна.")
        else:
            self._next_listener_retry = self._clock() + self._retry_delay
            self._retry_delay = min(self._retry_delay * 2, self.RETRY_DELAY_MAX)

    def reload(self) -> None:
        self.cfg = config.load()
        self.icon.title = self._title()
        self.start_listener()
        self.notify(f"Настройките са приложени. Комбинация: {config.hotkey_label(self.cfg['hotkey'])}")

    def _watch_config(self) -> None:
        """Презарежда настройките, когато файлът бъде променен (от прозореца за настройки)."""
        path = config.config_path()
        last = os.path.getmtime(path) if os.path.exists(path) else None
        tick = 0
        while not self._stop.is_set():
            time.sleep(1.0)
            tick += 1
            if tick % 3 == 0:
                try:
                    self._retry_listener_if_permitted()
                except Exception:
                    log.exception("Listener retry failed")
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
        listener, self.listener = self.listener, None   # за да не го рестартира _watch_config
        self.listener_ok = False
        if listener is not None:
            listener.stop()
        self.icon.stop()
