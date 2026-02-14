#!/usr/bin/env python3
"""
Website Watchdog - System Monitoring
Checks configured endpoints and alerts on failures
"""

import sqlite3
import time
import sys
import os
import json
from datetime import datetime
from pathlib import Path
import yaml
import requests
from dotenv import load_dotenv

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from alerter import Alerter

load_dotenv(PROJECT_ROOT / ".env")

class WatchdogDB:
    """Handle database operations"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def init_schema(self):
        """Initialize database schema"""
        schema_path = PROJECT_ROOT / "db" / "schema.sql"
        with open(schema_path) as f:
            self.conn.executescript(f.read())
        self.conn.commit()
        print(f"✓ Database initialized: {self.db_path}")
    
    def load_targets_from_config(self, config_path):
        """Load targets from YAML config into database"""
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        cursor = self.conn.cursor()
        
        for target in config.get('targets', []):
            cursor.execute("""
                INSERT OR REPLACE INTO targets 
                (name, url, method, expected_status, timeout, contains, alert_channels)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                target['name'],
                target['url'],
                target.get('method', 'GET'),
                target.get('expected_status', 200),
                target.get('timeout', 10),
                target.get('contains'),
                json.dumps(target.get('alert_channels', ['slack']))
            ))
        
        self.conn.commit()
        print(f"✓ Loaded {len(config['targets'])} targets from config")
    
    def get_active_targets(self):
        """Get all enabled monitoring targets"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM targets WHERE enabled = 1")
        return cursor.fetchall()
    
    def record_check(self, target_id, status, status_code=None, response_time=None, error_message=None):
        """Record a check result"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO checks (target_id, status, status_code, response_time, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (target_id, status, status_code, response_time, error_message))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_open_incident(self, target_id):
        """Get open incident for target, if any"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM incidents 
            WHERE target_id = ? AND status = 'open'
            ORDER BY started_at DESC LIMIT 1
        """, (target_id,))
        return cursor.fetchone()
    
    def create_incident(self, target_id, check_id):
        """Create new incident"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO incidents (target_id, last_check_id, failure_count)
            VALUES (?, ?, 1)
        """, (target_id, check_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_incident(self, incident_id, check_id, increment_count=True):
        """Update existing incident"""
        cursor = self.conn.cursor()
        if increment_count:
            cursor.execute("""
                UPDATE incidents 
                SET last_check_id = ?, failure_count = failure_count + 1
                WHERE id = ?
            """, (check_id, incident_id))
        else:
            cursor.execute("""
                UPDATE incidents 
                SET last_check_id = ?
                WHERE id = ?
            """, (check_id, incident_id))
        self.conn.commit()
    
    def resolve_incident(self, incident_id):
        """Mark incident as resolved"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE incidents 
            SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (incident_id,))
        self.conn.commit()
    
    def mark_alert_sent(self, incident_id, channel):
        """Mark that alert was sent via channel"""
        cursor = self.conn.cursor()
        column = f"{channel}_alerted"
        cursor.execute(f"""
            UPDATE incidents 
            SET {column} = 1
            WHERE id = ?
        """, (incident_id,))
        self.conn.commit()


class Watchdog:
    """Main monitoring watchdog"""
    
    def __init__(self, db_path, config_path):
        self.db = WatchdogDB(db_path)
        self.config_path = config_path
        self.alerter = Alerter(config_path)
    
    def init(self):
        """Initialize database and load config"""
        self.db.connect()
        self.db.init_schema()
        self.db.load_targets_from_config(self.config_path)
    
    def check_target(self, target):
        """Check a single target"""
        target_id = target['id']
        name = target['name']
        url = target['url']
        
        print(f"Checking {name}...", end=" ")
        
        start_time = time.time()
        
        try:
            response = requests.request(
                method=target['method'],
                url=url,
                timeout=target['timeout']
            )
            
            response_time = (time.time() - start_time) * 1000  # ms
            status_code = response.status_code
            
            # Check status code
            if status_code != target['expected_status']:
                status = 'failure'
                error_msg = f"Expected {target['expected_status']}, got {status_code}"
                print(f"✗ FAIL ({error_msg})")
            # Check content if specified
            elif target['contains'] and target['contains'] not in response.text:
                status = 'failure'
                error_msg = f"Expected content '{target['contains']}' not found"
                print(f"✗ FAIL ({error_msg})")
            else:
                status = 'success'
                error_msg = None
                print(f"✓ OK ({response_time:.0f}ms)")
            
            check_id = self.db.record_check(
                target_id, status, status_code, response_time, error_msg
            )
            
            return {
                'target_id': target_id,
                'name': name,
                'status': status,
                'status_code': status_code,
                'response_time': response_time,
                'error_message': error_msg,
                'check_id': check_id,
                'alert_channels': json.loads(target['alert_channels'])
            }
            
        except requests.Timeout:
            print(f"✗ TIMEOUT")
            check_id = self.db.record_check(
                target_id, 'timeout', None, None, f"Timeout after {target['timeout']}s"
            )
            return {
                'target_id': target_id,
                'name': name,
                'status': 'timeout',
                'error_message': f"Timeout after {target['timeout']}s",
                'check_id': check_id,
                'alert_channels': json.loads(target['alert_channels'])
            }
            
        except Exception as e:
            print(f"✗ ERROR: {e}")
            check_id = self.db.record_check(
                target_id, 'error', None, None, str(e)
            )
            return {
                'target_id': target_id,
                'name': name,
                'status': 'error',
                'error_message': str(e),
                'check_id': check_id,
                'alert_channels': json.loads(target['alert_channels'])
            }
    
    def handle_result(self, result):
        """Handle check result and trigger alerts if needed"""
        target_id = result['target_id']
        status = result['status']
        check_id = result['check_id']
        
        # Get existing open incident
        incident = self.db.get_open_incident(target_id)
        
        if status == 'success':
            # Recovery
            if incident:
                print(f"  → Incident resolved (was down {incident['failure_count']} checks)")
                self.db.resolve_incident(incident['id'])
                self.alerter.send_recovery_alert(result, incident)
        else:
            # Failure
            if incident:
                # Ongoing incident
                self.db.update_incident(incident['id'], check_id, increment_count=True)
                failure_count = incident['failure_count'] + 1
                print(f"  → Incident continues ({failure_count} consecutive failures)")
                
                # Escalate alerts based on failure count
                self.alerter.send_escalation_alert(result, incident, failure_count)
                
            else:
                # New incident
                incident_id = self.db.create_incident(target_id, check_id)
                print(f"  → New incident created (#{incident_id})")
                
                # Send initial alert
                self.alerter.send_initial_alert(result)
                
                # Mark alerts as sent in database
                for channel in result.get('alert_channels', ['slack']):
                    if channel in ['slack', 'email', 'sms']:
                        self.db.mark_alert_sent(incident_id, channel)
    
    def run_checks(self):
        """Run checks on all active targets"""
        self.db.connect()
        targets = self.db.get_active_targets()
        
        if not targets:
            print("No active targets configured.")
            return
        
        print(f"\n=== Website Watchdog - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        
        for target in targets:
            result = self.check_target(target)
            self.handle_result(result)
        
        print(f"\n=== Check complete ===\n")


def main():
    """Main entry point"""
    db_path = PROJECT_ROOT / "db" / "watchdog.db"
    config_path = PROJECT_ROOT / "config" / "targets.yaml"
    
    watchdog = Watchdog(db_path, config_path)
    
    # Parse command
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    
    if command == "init":
        print("Initializing watchdog...")
        watchdog.init()
        print("✓ Watchdog initialized successfully")
        
    elif command == "check":
        watchdog.run_checks()
        
    else:
        print(f"Unknown command: {command}")
        print("Usage: watchdog.py [init|check]")
        sys.exit(1)


if __name__ == "__main__":
    main()
