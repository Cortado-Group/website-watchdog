# Website Watchdog

System monitoring watchdog for Cortado Group applications.

## Features

- **Multi-target monitoring**: HTTP endpoints, response time, status codes, content validation
- **Local SQLite database**: Persistent check history and incident tracking
- **Smart alerting**: 
  - First failure: Slack notification
  - Sustained failure (3+ consecutive): Email + SMS escalation
  - Recovery notifications
- **5-minute check interval** (configurable)

## Architecture

```
watchdog.py     - Main monitoring loop
alerter.py      - Multi-channel notification handler
config/         - Monitoring targets configuration
db/             - SQLite database and schema
logs/           - Check logs and debugging
```

## Setup

```bash
cd ~/work/website_watchdog
pip3 install -r requirements.txt
python3 watchdog.py init  # Initialize database
python3 watchdog.py check # Run one-time check
```

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

## Testing

Run comprehensive test suite (30 tests, ~56% coverage):

```bash
./run_tests.sh
```

See `TESTING.md` for detailed testing documentation.

## Cron Setup

Run every 5 minutes:

```bash
*/5 * * * * cd ~/work/website_watchdog && /opt/homebrew/bin/python3 watchdog.py check >> logs/cron.log 2>&1
```

## Database Schema

- `checks`: All monitoring checks (timestamp, target, status, response_time)
- `incidents`: Active/resolved incidents with alert history
- `targets`: Monitored endpoints configuration

## Alert Channels

- **Slack**: Immediate notifications to configured channel
- **Email**: Escalation for sustained failures
- **SMS**: Critical escalation (via Twilio or email-to-SMS gateway)
