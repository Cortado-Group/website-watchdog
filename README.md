# Website Watchdog

System monitoring watchdog for Cortado Group applications.

**🔗 GitHub**: https://github.com/Cortado-Group/website-watchdog

## Features

- **Multi-target monitoring**: HTTP endpoints, response time, status codes, content validation
- **Local SQLite database**: Persistent check history and incident tracking
- **Smart alerting**: 
  - First failure: Slack notification
  - Sustained failure (3+ consecutive): Email + SMS escalation
  - Recovery notifications
- **macOS LaunchAgent service**: Auto-start, logging, restart on failure
- **5-minute check interval** (configurable)
- **Comprehensive test suite**: 30 tests, 83% core coverage

## Quick Start

```bash
cd ~/work/website_watchdog

# 1. Run setup
./setup.sh

# 2. Configure alerts
nano .env  # Add SMTP/Slack credentials

# 3. Install as service
./install_service.sh

# 4. Check status
./service_status.sh
```

See `QUICKSTART.md` for detailed setup instructions.

## Architecture

```
watchdog.py     - Main monitoring loop
alerter.py      - Multi-channel notification handler
config/         - Monitoring targets configuration
db/             - SQLite database and schema
logs/           - Check logs and debugging
```

## Documentation

- **`QUICKSTART.md`** - 5-minute setup guide
- **`SERVICE.md`** - Service management & troubleshooting
- **`ALERTS.md`** - Alert configuration (Slack, Email, SMS)
- **`TESTING.md`** - Test suite documentation
- **`TEST_SUMMARY.md`** - Coverage report

## Configuration

Edit `config/targets.yaml` to add endpoints:

```yaml
targets:
  - name: "Django Project Dev"
    url: "https://cg.cortadogroup.dev/api/version/"
    method: GET
    expected_status: 200
    timeout: 10
    alert_channels: [slack, email]
  
  - name: "Main Website"
    url: "https://cortadogroup.com"
    method: GET
    expected_status: 200
    contains: "Cortado Group"
    timeout: 5
    alert_channels: [slack, email, sms]
```

## Service Management

```bash
# Check status
./service_status.sh

# View monitoring stats
source venv/bin/activate
python3 status.py

# Watch logs
tail -f logs/service.log

# Stop service
./uninstall_service.sh
```

## Testing

Run comprehensive test suite (30 tests, 83% core coverage):

```bash
./run_tests.sh
```

See `TESTING.md` for detailed testing documentation.

## Alert Channels

- **Slack**: Immediate notifications (via Clawdbot or webhook)
- **Email**: Escalation after 3 consecutive failures (via SMTP)
- **SMS**: Critical escalation after 5 failures (via Twilio or email gateway)

See `ALERTS.md` for configuration details.

## Database Schema

- `checks`: All monitoring checks (timestamp, target, status, response_time)
- `incidents`: Active/resolved incidents with alert history
- `targets`: Monitored endpoints configuration

## Requirements

- Python 3.9+
- macOS (for LaunchAgent service)
- Virtual environment recommended

## Installation

```bash
git clone https://github.com/Cortado-Group/website-watchdog.git
cd website-watchdog
./setup.sh
./install_service.sh
```

## Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_watchdog.py -v

# Initialize database
python3 watchdog.py init

# Run single check
python3 watchdog.py check
```

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests (`./run_tests.sh`)
5. Submit a pull request

## Support

- **Issues**: https://github.com/Cortado-Group/website-watchdog/issues
- **Docs**: See documentation files in this repo
- **Slack**: #engineering (Cortado Group workspace)

---

**Built with ❤️ by Cortado Group**

🎵 Maintained by Kiselgolem (the silicon guardian)
