#!/bin/bash
# Website Watchdog - Setup Script

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🔧 Setting up Website Watchdog..."
echo

# Install Python dependencies
echo "📦 Installing Python packages..."
pip3 install -r requirements.txt
echo

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your credentials"
    echo
fi

# Initialize database
echo "🗄️  Initializing database..."
python3 watchdog.py init
echo

# Test configuration
echo "🧪 Running test check..."
python3 watchdog.py check
echo

echo "✅ Setup complete!"
echo
echo "Next steps:"
echo "1. Edit .env with your alert credentials"
echo "2. Edit config/targets.yaml to add your endpoints"
echo "3. Set up cron job:"
echo "   */5 * * * * cd $PROJECT_DIR && /opt/homebrew/bin/python3 watchdog.py check >> logs/cron.log 2>&1"
echo
