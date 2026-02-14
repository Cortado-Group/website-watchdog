#!/usr/bin/env python3
"""
Alert Handler - Multi-channel notifications
Supports: Slack, Email, SMS
"""

import os
import json
import smtplib
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import yaml


class Alerter:
    """Handle alerts via multiple channels"""
    
    def __init__(self, config_path):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.alert_config = self.config.get('alerts', {})
    
    def send_initial_alert(self, result):
        """Send initial failure alert"""
        message = self._format_failure_message(result)
        
        # Always send to Slack first (immediate notification)
        if 'slack' in result.get('alert_channels', []):
            self._send_slack(
                f"🚨 ALERT: {result['name']} is DOWN",
                message,
                color='danger'
            )
    
    def send_escalation_alert(self, result, incident, failure_count):
        """Send escalated alerts based on failure count"""
        alert_config = self.alert_config
        
        # Email escalation
        email_config = alert_config.get('email', {})
        email_threshold = email_config.get('escalate_after', 3)
        
        if (failure_count == email_threshold and 
            'email' in result.get('alert_channels', []) and
            email_config.get('enabled', True)):
            
            message = self._format_failure_message(result, failure_count)
            self._send_email(
                subject=f"🚨 ESCALATION: {result['name']} down for {failure_count} checks",
                body=message,
                recipients=email_config.get('recipients', [])
            )
            print(f"  → Email alert sent (escalation threshold reached)")
        
        # SMS escalation
        sms_config = alert_config.get('sms', {})
        sms_threshold = sms_config.get('escalate_after', 5)
        
        if (failure_count == sms_threshold and 
            'sms' in result.get('alert_channels', []) and
            sms_config.get('enabled', False)):
            
            brief_message = f"CRITICAL: {result['name']} has been down for {failure_count} consecutive checks. {result.get('error_message', 'Unknown error')}"
            self._send_sms(brief_message, sms_config)
            print(f"  → SMS alert sent (critical threshold reached)")
    
    def send_recovery_alert(self, result, incident):
        """Send recovery notification"""
        downtime = incident['failure_count']
        message = f"✅ *RECOVERED*: {result['name']}\n\n"
        message += f"Target is now responding normally.\n"
        message += f"Was down for {downtime} consecutive checks.\n"
        message += f"Response time: {result.get('response_time', 0):.0f}ms"
        
        if 'slack' in result.get('alert_channels', []):
            self._send_slack(
                f"✅ RECOVERED: {result['name']}",
                message,
                color='good'
            )
    
    def _format_failure_message(self, result, failure_count=1):
        """Format failure message"""
        msg = f"*Target*: {result['name']}\n"
        msg += f"*Status*: {result['status'].upper()}\n"
        
        if result.get('status_code'):
            msg += f"*HTTP Status*: {result['status_code']}\n"
        
        if result.get('error_message'):
            msg += f"*Error*: {result['error_message']}\n"
        
        if failure_count > 1:
            msg += f"*Consecutive Failures*: {failure_count}\n"
        
        msg += f"*Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return msg
    
    def _send_slack(self, title, message, color='danger'):
        """Send Slack notification"""
        slack_config = self.alert_config.get('slack', {})
        
        if not slack_config.get('enabled', True):
            return
        
        channel = slack_config.get('channel', '#alerts')
        
        # Try using Clawdbot message tool (via subprocess)
        try:
            # Format as blocks for better appearance
            full_message = f"*{title}*\n\n{message}"
            
            # Use clawdbot CLI to send message
            cmd = [
                'clawdbot', 'message',
                '--channel', 'slack',
                '--to', channel,
                '--message', full_message
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"  → Slack alert sent to {channel}")
            else:
                print(f"  → Slack alert failed: {result.stderr}")
                
        except Exception as e:
            print(f"  → Slack alert error: {e}")
    
    def _send_email(self, subject, body, recipients):
        """Send email via SMTP"""
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('EMAIL_FROM', smtp_user)
        
        if not all([smtp_host, smtp_user, smtp_pass]):
            print("  → Email alert skipped (SMTP not configured)")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            
            print(f"  → Email sent to {', '.join(recipients)}")
            
        except Exception as e:
            print(f"  → Email error: {e}")
    
    def _send_sms(self, message, sms_config):
        """Send SMS via Twilio or email gateway"""
        method = sms_config.get('method', 'email_gateway')
        
        if method == 'twilio':
            self._send_sms_twilio(message, sms_config)
        else:
            self._send_sms_email_gateway(message, sms_config)
    
    def _send_sms_twilio(self, message, sms_config):
        """Send SMS via Twilio API"""
        try:
            from twilio.rest import Client
            
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            from_number = os.getenv('TWILIO_FROM_NUMBER')
            
            if not all([account_sid, auth_token, from_number]):
                print("  → SMS skipped (Twilio not configured)")
                return
            
            client = Client(account_sid, auth_token)
            
            for recipient in sms_config.get('recipients', []):
                client.messages.create(
                    body=message,
                    from_=from_number,
                    to=recipient
                )
            
            print(f"  → SMS sent via Twilio")
            
        except ImportError:
            print("  → SMS error: twilio package not installed (pip install twilio)")
        except Exception as e:
            print(f"  → SMS error: {e}")
    
    def _send_sms_email_gateway(self, message, sms_config):
        """Send SMS via email-to-SMS gateway (simpler, no API needed)"""
        gateway = os.getenv('SMS_EMAIL_GATEWAY')
        
        if not gateway:
            print("  → SMS skipped (SMS_EMAIL_GATEWAY not configured)")
            return
        
        # Send via SMTP to email-to-SMS gateway
        self._send_email(
            subject="Watchdog Alert",
            body=message[:160],  # SMS limit
            recipients=[gateway]
        )
        print(f"  → SMS sent via email gateway")


if __name__ == "__main__":
    # Test alerter
    from pathlib import Path
    config_path = Path(__file__).parent / "config" / "targets.yaml"
    
    alerter = Alerter(config_path)
    
    test_result = {
        'name': 'Test Service',
        'status': 'failure',
        'status_code': 500,
        'error_message': 'Internal Server Error',
        'alert_channels': ['slack']
    }
    
    print("Sending test alert...")
    alerter.send_initial_alert(test_result)
    print("Test complete")
