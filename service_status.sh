#!/bin/bash
# Check Website Watchdog service status

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "📊 Website Watchdog Service Status"
echo "==================================="
echo

# Check if service is loaded
if launchctl print gui/$(id -u)/com.cortadogroup.watchdog &>/dev/null; then
    echo "✅ Service: INSTALLED"
    echo
    
    # Get service info
    launchctl print gui/$(id -u)/com.cortadogroup.watchdog | grep -E "state|last exit"
    
else
    echo "❌ Service: NOT INSTALLED"
fi

echo
echo "📂 Files:"
echo "  Config: ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist"
echo "  Database: $PROJECT_DIR/db/watchdog.db"
echo "  Log: $PROJECT_DIR/logs/service.log"
echo "  Errors: $PROJECT_DIR/logs/service_error.log"
echo

# Check if database exists
if [ -f "$PROJECT_DIR/db/watchdog.db" ]; then
    echo "✅ Database: EXISTS"
    
    # Show recent activity
    if [ -f "$PROJECT_DIR/logs/service.log" ]; then
        echo
        echo "📝 Recent Activity (last 10 lines):"
        echo "-----------------------------------"
        tail -10 "$PROJECT_DIR/logs/service.log"
    fi
else
    echo "❌ Database: NOT INITIALIZED"
    echo "   Run: ./setup.sh"
fi

echo
echo "Commands:"
echo "  Restart:  launchctl unload ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist && launchctl load ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist"
echo "  Stop:     ./uninstall_service.sh"
echo "  Logs:     tail -f $PROJECT_DIR/logs/service.log"
echo "  Status:   python3 $PROJECT_DIR/status.py"
