#!/usr/bin/env bash
# KirLat – деинсталация за macOS:
#   curl -fsSL https://raw.githubusercontent.com/NPashofff/KirLat/main/uninstall.sh | bash
set -uo pipefail

PLIST="$HOME/Library/LaunchAgents/com.kirlat.app.plist"
pkill -x KirLat 2>/dev/null || true
launchctl unload -w "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
rm -rf /Applications/KirLat.app
rm -rf "$HOME/Library/Application Support/KirLat"   # настройки и дневник
echo "KirLat е премахнат. Може да махнете и записа му от Privacy & Security → Accessibility."
