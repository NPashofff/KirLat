"""Генерира assets/icon.png, assets/icon.ico и (на macOS) assets/icon.icns."""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kirlat.icon import make_icon_image  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(ASSETS, exist_ok=True)

big = make_icon_image(1024)
big.save(os.path.join(ASSETS, "icon.png"))
make_icon_image(256).save(os.path.join(ASSETS, "icon.ico"),
                          sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("assets/icon.png, assets/icon.ico")

if sys.platform == "darwin" and shutil.which("iconutil"):
    iconset = os.path.join(ASSETS, "icon.iconset")
    os.makedirs(iconset, exist_ok=True)
    for s in (16, 32, 64, 128, 256, 512):
        make_icon_image(s).save(os.path.join(iconset, f"icon_{s}x{s}.png"))
        make_icon_image(s * 2).save(os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(ASSETS, "icon.icns")], check=True)
    shutil.rmtree(iconset)
    print("assets/icon.icns")
