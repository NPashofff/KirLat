# -*- mode: python ; coding: utf-8 -*-
# PyInstaller спецификация – работи и за Windows (.exe), и за macOS (.app).
import os
import sys

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")
HERE = os.path.abspath(".")

if IS_WIN:
    hidden = ["pystray._win32", "pynput.keyboard._win32", "pynput.mouse._win32"]
    icon = os.path.join(HERE, "assets", "icon.ico")
elif IS_MAC:
    hidden = ["pystray._darwin", "pynput.keyboard._darwin", "pynput.mouse._darwin",
              "Quartz", "AppKit", "ApplicationServices"]
    icon = os.path.join(HERE, "assets", "icon.icns")
else:
    hidden = ["pystray._xorg", "pynput.keyboard._xorg", "pynput.mouse._xorg"]
    icon = None
if icon and not os.path.exists(icon):
    icon = None

a = Analysis(
    ["main.py"],
    pathex=[HERE],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

if IS_MAC:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="KirLat",
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon=icon,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="KirLat")
    app = BUNDLE(
        coll,
        name="KirLat.app",
        icon=icon,
        bundle_identifier="com.kirlat.app",
        info_plist={
            "CFBundleName": "KirLat",
            "CFBundleDisplayName": "KirLat",
            "CFBundleShortVersionString": "1.0.0",
            "LSUIElement": True,          # без икона в Dock – само в лентата с менюта
            "NSHighResolutionCapable": True,
            "NSAppleEventsUsageDescription": "KirLat симулира Cmd+C/Cmd+V, за да замени селектирания текст.",
        },
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="KirLat",
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon=icon,
    )
