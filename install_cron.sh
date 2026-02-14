#!/bin/bash
# Install cron job for watchdog

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)

# Create cron job
CRON_CMD="*/5 * * * * cd $PROJECT_DIR && $PYTHON_PATH watchdog.py check >> logs/cron.log 2>&1"

echo "Installing cron job:"
echo "$CRON_CMD"
echo

# Check if already exists
if crontab -l 2>/dev/null | grep -q "watchdog.py check"; then
    echo "⚠️  Watchdog cron job already exists!"
    echo "Run 'crontab -e' to edit manually"
    exit 1
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job installed successfully"
echo
echo "Check status with: crontab -l"
echo "View logs at: $PROJECT_DIR/logs/cron.log"
