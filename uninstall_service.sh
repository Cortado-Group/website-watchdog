#!/bin/bash
# Uninstall Website Watchdog service

PLIST_NAME="com.cortadogroup.watchdog.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🛑 Uninstalling Website Watchdog Service"
echo "========================================"
echo

if [ ! -f "$PLIST_PATH" ]; then
    echo "⚠️  Service not installed (plist not found)"
    exit 0
fi

# Unload service
if launchctl print gui/$(id -u)/com.cortadogroup.watchdog &>/dev/null; then
    echo "⏹️  Stopping service..."
    launchctl bootout gui/$(id -u)/com.cortadogroup.watchdog
    echo "✓ Service stopped"
else
    echo "ℹ️  Service not running"
fi

# Remove plist
echo "🗑️  Removing configuration..."
rm "$PLIST_PATH"
echo "✓ Service uninstalled"
echo

echo "✅ Uninstall complete"
echo
echo "Note: Database and logs remain in ~/work/website_watchdog/"
echo "To remove completely: rm -rf ~/work/website_watchdog/"
