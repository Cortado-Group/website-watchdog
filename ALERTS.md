# Alert Configuration Guide

## Slack Alerts

### Option 1: Via Clawdbot (Recommended)

The watchdog can send Slack alerts via Clawdbot's message routing.

**Current implementation assumes:**
```bash
clawdbot send slack <channel> <message>
```

**If your clawdbot syntax is different**, edit `alerter.py` line ~120:

```python
# Current:
cmd = ['clawdbot', 'send', 'slack', channel, full_message]

# Alternative syntaxes you might need:
# cmd = ['clawdbot', 'message', '--to', channel, '--text', full_message]
# cmd = ['clawdbot', 'slack', 'send', '--channel', channel, '--message', full_message]
```

**Or use Clawdbot as a library:**

```python
# If running within Clawdbot context, use the message tool directly
from clawdbot import message
message.send(channel='slack', to=channel, message=full_message)
```

### Option 2: Direct Slack Webhook

More reliable, no Clawdbot dependency:

1. Create Slack webhook: https://api.slack.com/messaging/webhooks
2. Add to `.env`:
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

3. Update `alerter.py` `_send_slack()`:

```python
def _send_slack(self, title, message, color='danger'):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("  → Slack webhook not configured")
        return
    
    payload = {
        "text": f"*{title}*",
        "attachments": [{
            "color": color,
            "text": message
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"  → Slack alert sent")
        else:
            print(f"  → Slack alert failed: {response.status_code}")
    except Exception as e:
        print(f"  → Slack error: {e}")
```

### Option 3: Slack API (Most Features)

For advanced features (threads, reactions, etc.):

1. Create Slack app with chat:write scope
2. Add to `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL=C01234ABCD  # Channel ID
```

3. Install slack-sdk:
```bash
pip install slack-sdk
```

4. Update `alerter.py`:

```python
from slack_sdk import WebClient

def _send_slack(self, title, message, color='danger'):
    token = os.getenv('SLACK_BOT_TOKEN')
    channel = os.getenv('SLACK_CHANNEL')
    
    if not token or not channel:
        print("  → Slack not configured")
        return
    
    client = WebClient(token=token)
    
    try:
        client.chat_postMessage(
            channel=channel,
            text=f"*{title}*\n\n{message}"
        )
        print(f"  → Slack alert sent to {channel}")
    except Exception as e:
        print(f"  → Slack error: {e}")
```

## Email Alerts

### SMTP Configuration

Add to `.env`:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use App Password, not regular password!
EMAIL_FROM=watchdog@cortadogroup.com
EMAIL_TO=alerts@cortadogroup.com
```

### Gmail Setup

1. Enable 2FA on your Google account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use App Password in `.env`, not your regular password

### Other SMTP Providers

**SendGrid:**
```
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

**Mailgun:**
```
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-smtp-password
```

**Office 365:**
```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-password
```

## SMS Alerts

### Option 1: Email-to-SMS Gateway (Free, Simple)

Most carriers have email-to-SMS gateways:

```bash
# Add to .env:
SMS_EMAIL_GATEWAY=5551234567@txt.att.net
```

**Carrier Gateways:**
- AT&T: `number@txt.att.net`
- Verizon: `number@vtext.com`
- T-Mobile: `number@tmomail.net`
- Sprint: `number@messaging.sprintpcs.com`
- US Cellular: `number@email.uscc.net`

Messages are limited to ~160 characters.

### Option 2: Twilio (Reliable, Costs $$$)

1. Sign up at https://twilio.com
2. Get account SID, auth token, and phone number
3. Add to `.env`:

```bash
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_FROM_NUMBER=+15551234567
TWILIO_TO_NUMBER=+15559876543
```

4. Install Twilio SDK:
```bash
pip install twilio
```

5. Enable in `config/targets.yaml`:
```yaml
alerts:
  sms:
    enabled: true
    method: "twilio"
```

## Alert Escalation

Configure escalation thresholds in `config/targets.yaml`:

```yaml
alerts:
  slack:
    enabled: true
    channel: "#alerts"
  
  email:
    enabled: true
    recipients:
      - "oncall@company.com"
      - "team-lead@company.com"
    escalate_after: 3  # Send after 3 consecutive failures
  
  sms:
    enabled: true
    recipients:
      - "+15551234567"
    escalate_after: 5  # Send after 5 consecutive failures (critical only)
    method: "email_gateway"  # or "twilio"
```

**Escalation Flow:**
1. **First failure** → Slack notification
2. **3rd consecutive failure** → Email escalation
3. **5th consecutive failure** → SMS escalation (critical alert)
4. **Recovery** → Slack notification (all clear)

## Testing Alerts

### Test Slack
```python
cd ~/work/website_watchdog
source venv/bin/activate
python3 -c "
from alerter import Alerter
from pathlib import Path

config = Path('config/targets.yaml')
alerter = Alerter(config)

result = {
    'name': 'Test Service',
    'status': 'failure',
    'error_message': 'Test alert',
    'alert_channels': ['slack']
}

alerter.send_initial_alert(result)
"
```

### Test Email
```bash
# Make sure SMTP credentials are in .env
python3 -c "
from alerter import Alerter
from pathlib import Path

alerter = Alerter(Path('config/targets.yaml'))
alerter._send_email(
    subject='Test Alert',
    body='This is a test email from Website Watchdog',
    recipients=['your-email@example.com']
)
"
```

### Test SMS
```bash
# If using email gateway:
python3 -c "
from alerter import Alerter
alerter = Alerter('config/targets.yaml')
alerter._send_sms_email_gateway(
    'Test SMS',
    {'recipients': ['+15551234567']}
)
"
```

## Custom Alert Channels

Want to add Discord, PagerDuty, or custom webhooks?

Edit `alerter.py` and add your handler:

```python
def _send_discord(self, title, message):
    """Send Discord webhook"""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    payload = {
        "content": f"**{title}**\n\n{message}"
    }
    
    requests.post(webhook_url, json=payload)

def _send_pagerduty(self, title, message):
    """Send PagerDuty incident"""
    routing_key = os.getenv('PAGERDUTY_ROUTING_KEY')
    
    payload = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": title,
            "severity": "error",
            "source": "website-watchdog",
            "custom_details": {"message": message}
        }
    }
    
    requests.post(
        "https://events.pagerduty.com/v2/enqueue",
        json=payload
    )
```

## Troubleshooting

### Slack Not Sending

```bash
# Check if clawdbot is installed
which clawdbot

# Test clawdbot command manually
clawdbot send slack "#test" "Hello from watchdog"

# Check service logs
tail -f logs/service.log
```

### Email Not Sending

```bash
# Test SMTP credentials
python3 -c "
import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

server = smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT')))
server.starttls()
server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
print('✓ SMTP connection successful')
server.quit()
"
```

### No Alerts at All

```bash
# Verify target has alert_channels configured
cat config/targets.yaml | grep -A5 alert_channels

# Check database for incidents
python3 status.py incidents

# Test alerter directly
python3 alerter.py
```

## Best Practices

1. **Test your alerts** before relying on them
2. **Set appropriate thresholds** to avoid alert fatigue
3. **Use different channels** for different severity levels
4. **Include context** in alerts (what failed, when, how many times)
5. **Send recovery notifications** so people know it's fixed
6. **Monitor your monitors** (who watches the watchdog?)

---

For more info, see:
- `README.md` - Full documentation
- `config/targets.yaml` - Alert configuration
- `alerter.py` - Alert implementation
