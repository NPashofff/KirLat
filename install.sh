#!/usr/bin/env bash
# KirLat – инсталация за macOS с една команда:
#   curl -fsSL https://raw.githubusercontent.com/NPashofff/KirLat/main/install.sh | bash
# Сваля готовия KirLat.app от GitHub Releases (или го билдва от изходния код, ако няма),
# слага го в /Applications, включва автостарт и го стартира.
set -euo pipefail

REPO="NPashofff/KirLat"
APP="/Applications/KirLat.app"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Този скрипт е за macOS. За Windows: irm https://raw.githubusercontent.com/$REPO/main/install.ps1 | iex"
  exit 1
fi

echo "KirLat: търся последната версия..."
url="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
      | grep -o '"browser_download_url": *"[^"]*KirLat-macOS\.zip"' \
      | head -1 | sed 's/.*"\(https[^"]*\)"/\1/' || true)"

if [ -n "$url" ]; then
  echo "KirLat: свалям готовия билд..."
  curl -fsSL "$url" -o "$TMP/KirLat-macOS.zip"
  ditto -x -k "$TMP/KirLat-macOS.zip" "$TMP/unzipped"
  BUILT="$(find "$TMP/unzipped" -maxdepth 2 -name 'KirLat.app' | head -1)"
else
  echo "KirLat: няма готов macOS билд – билдвам от изходния код (нужен е python3 с tkinter)..."
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.tar.gz" | tar -xz -C "$TMP"
  (cd "$TMP/KirLat-main" && chmod +x build_macos.sh && ./build_macos.sh)
  BUILT="$TMP/KirLat-main/dist/KirLat.app"
fi
[ -d "$BUILT" ] || { echo "KirLat.app не е намерен"; exit 1; }

pkill -x KirLat 2>/dev/null || true
rm -rf "$APP"
cp -R "$BUILT" "$APP"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

# Автостарт при вход (LaunchAgent) – същият файл, който приложението управлява от настройките
PLIST="$HOME/Library/LaunchAgents/com.kirlat.app.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.kirlat.app</string>
  <key>ProgramArguments</key><array><string>$APP/Contents/MacOS/KirLat</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
  <key>ProcessType</key><string>Interactive</string>
</dict></plist>
EOF
launchctl unload -w "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST" 2>/dev/null || true

open -a "$APP"
echo
echo "KirLat е инсталиран в $APP и стартиран (иконата е в лентата с менюта)."
echo "ВАЖНО: разрешете го в System Settings → Privacy & Security → Accessibility и Input Monitoring,"
echo "после го рестартирайте. Селектирайте текст и натиснете Ctrl+W."
echo "Деинсталиране: curl -fsSL https://raw.githubusercontent.com/$REPO/main/uninstall.sh | bash"
