#!/bin/bash
# Install Website Watchdog as macOS LaunchAgent

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_NAME="com.cortadogroup.watchdog.plist"
PLIST_SOURCE="$PROJECT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🔧 Installing Website Watchdog Service"
echo "======================================="
echo

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Create venv if it doesn't exist
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
    source "$PROJECT_DIR/venv/bin/activate"
    pip install -q -r "$PROJECT_DIR/requirements.txt"
    echo "✓ Virtual environment created"
    echo
fi

# Initialize database if needed
if [ ! -f "$PROJECT_DIR/db/watchdog.db" ]; then
    echo "🗄️  Initializing database..."
    source "$PROJECT_DIR/venv/bin/activate"
    python3 "$PROJECT_DIR/watchdog.py" init
    echo
fi

# Stop existing service if running
if launchctl print gui/$(id -u)/com.cortadogroup.watchdog &>/dev/null; then
    echo "⏸️  Stopping existing service..."
    launchctl bootout gui/$(id -u)/com.cortadogroup.watchdog 2>/dev/null || true
    echo
fi

# Copy plist to LaunchAgents
echo "📝 Installing service configuration..."
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "✓ Copied to ~/Library/LaunchAgents/"
echo

# Load the service
echo "▶️  Starting service..."
launchctl bootstrap gui/$(id -u) "$PLIST_DEST"
echo

# Check status
sleep 2
if launchctl print gui/$(id -u)/com.cortadogroup.watchdog &>/dev/null; then
    echo "✅ Service installed successfully!"
    echo
    echo "Service Details:"
    echo "  Name: com.cortadogroup.watchdog"
    echo "  Interval: Every 5 minutes"
    echo "  Logs: $PROJECT_DIR/logs/service.log"
    echo "  Errors: $PROJECT_DIR/logs/service_error.log"
    echo
    echo "Commands:"
    echo "  Status:  launchctl list | grep watchdog"
    echo "  Stop:    launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
    echo "  Start:   launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
    echo "  Logs:    tail -f $PROJECT_DIR/logs/service.log"
    echo
else
    echo "❌ Service failed to start!"
    echo "Check logs: $PROJECT_DIR/logs/service_error.log"
    exit 1
fi
