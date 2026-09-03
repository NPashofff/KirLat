#!/usr/bin/env bash
# Билд на KirLat.app за macOS. Изпълнява се на Mac. Резултат: dist/KirLat.app
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null; then
  echo "Нужен е python3 (brew install python или от python.org)"; exit 1
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt pyinstaller pyobjc-framework-Cocoa pyobjc-framework-Quartz pyobjc-framework-ApplicationServices
python make_icon.py
pyinstaller --noconfirm --clean KirLat.spec

# ad-hoc подпис, за да може macOS да запомни разрешенията (Accessibility / Input Monitoring)
codesign --force --deep --sign - dist/KirLat.app || true

echo
echo "Готово: $(pwd)/dist/KirLat.app"
echo "Копирайте го в /Applications и при първо стартиране разрешете Accessibility и Input Monitoring."
