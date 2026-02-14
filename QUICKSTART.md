# Quick Start Guide

## Initial Setup (5 minutes)

```bash
cd ~/work/website_watchdog

# 1. Run setup script
./setup.sh

# 2. Configure alerts
nano .env   # Add your SMTP/Slack credentials

# 3. Add monitoring targets
nano config/targets.yaml
```

## Add Monitoring Targets

Edit `config/targets.yaml`:

```yaml
targets:
  - name: "My API"
    url: "https://api.example.com/health"
    expected_status: 200
    timeout: 10
    alert_channels:
      - slack
      - email
```

Reload config:
```bash
python3 watchdog.py init
```

## Manual Check

Test your configuration:

```bash
python3 watchdog.py check
```

## View Status

```bash
python3 status.py              # Show everything
python3 status.py incidents    # Active incidents only
python3 status.py stats        # 24h uptime stats
python3 status.py checks 50    # Last 50 checks
```

## Install as Service (Recommended)

Install as macOS LaunchAgent (auto-start, better logging):

```bash
./install_service.sh
```

Check status:
```bash
./service_status.sh
```

Stop service:
```bash
./uninstall_service.sh
```

## Alternative: Install Cron

If you prefer cron instead of a service:

```bash
./install_cron.sh
```

Or manually add to crontab:
```
*/5 * * * * cd ~/work/website_watchdog && /opt/homebrew/bin/python3 watchdog.py check >> logs/cron.log 2>&1
```

## Alert Configuration

### Slack
Alerts use Clawdbot's `message` tool. Make sure Clawdbot is running:
```bash
clawdbot gateway status
```

### Email (SMTP)
Add to `.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=watchdog@cortadogroup.com
EMAIL_TO=david@cortadogroup.com
```

### SMS (Optional)

**Option 1: Email Gateway (Simpler)**
```
SMS_EMAIL_GATEWAY=5551234567@txt.att.net
```

Common gateways:
- AT&T: `number@txt.att.net`
- Verizon: `number@vtext.com`
- T-Mobile: `number@tmomail.net`

**Option 2: Twilio (More Reliable)**
```
pip3 install twilio
```
Add to `.env`:
```
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_FROM_NUMBER=+15551234567
TWILIO_TO_NUMBER=+15559876543
```

## Escalation Rules

- **First failure**: Slack notification
- **3 consecutive failures**: Email escalation
- **5 consecutive failures**: SMS escalation (if enabled)
- **Recovery**: Slack notification

Customize in `config/targets.yaml`:
```yaml
alerts:
  email:
    escalate_after: 3
  sms:
    escalate_after: 5
```

## Logs

- **Cron log**: `logs/cron.log`
- **Database**: `db/watchdog.db`

## Troubleshooting

**No alerts sent?**
```bash
# Test alerter directly
python3 alerter.py
```

**Database issues?**
```bash
# Reinitialize
rm db/watchdog.db
python3 watchdog.py init
```

**Check cron job:**
```bash
crontab -l
tail -f logs/cron.log
```

## Directory Structure

```
website_watchdog/
├── watchdog.py           # Main monitoring script
├── alerter.py            # Alert handler
├── status.py             # Status viewer
├── setup.sh              # Setup script
├── install_cron.sh       # Cron installer
├── config/
│   └── targets.yaml      # Monitoring targets
├── db/
│   ├── schema.sql        # Database schema
│   └── watchdog.db       # SQLite database
└── logs/
    └── cron.log          # Cron output
```
