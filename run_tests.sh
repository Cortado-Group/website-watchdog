#!/bin/bash
# Run all tests with coverage

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🧪 Running Website Watchdog Tests"
echo "=================================="
echo

# Install test dependencies if needed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "📦 Installing test dependencies..."
    pip3 install -r requirements.txt
    echo
fi

# Run tests
echo "🏃 Running test suite..."
echo

python3 -m pytest test_watchdog.py \
    -v \
    --tb=short \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html:coverage_html

TEST_RESULT=$?

echo
echo "=================================="

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ All tests passed!"
    echo
    echo "📊 Coverage report generated: coverage_html/index.html"
else
    echo "❌ Tests failed!"
    exit 1
fi

echo
