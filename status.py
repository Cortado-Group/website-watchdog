#!/usr/bin/env python3
"""
Watchdog Status Viewer
View current incidents, recent checks, and statistics
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from tabulate import tabulate

PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "db" / "watchdog.db"


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def show_incidents():
    """Show active incidents"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT i.*, t.name, t.url
        FROM incidents i
        JOIN targets t ON i.target_id = t.id
        WHERE i.status = 'open'
        ORDER BY i.started_at DESC
    """)
    
    incidents = cursor.fetchall()
    
    if not incidents:
        print("✅ No active incidents\n")
        return
    
    print(f"\n🚨 Active Incidents ({len(incidents)}):\n")
    
    for inc in incidents:
        print(f"#{inc['id']} - {inc['name']}")
        print(f"  Started: {inc['started_at']}")
        print(f"  Failures: {inc['failure_count']} consecutive")
        print(f"  Alerts: Slack={inc['slack_alerted']} Email={inc['email_alerted']} SMS={inc['sms_alerted']}")
        print()


def show_recent_checks(limit=20):
    """Show recent check history"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, t.name
        FROM checks c
        JOIN targets t ON c.target_id = t.id
        ORDER BY c.timestamp DESC
        LIMIT ?
    """, (limit,))
    
    checks = cursor.fetchall()
    
    print(f"\n📊 Recent Checks (last {limit}):\n")
    
    table = []
    for check in checks:
        status_icon = "✓" if check['status'] == 'success' else "✗"
        response_time = f"{check['response_time']:.0f}ms" if check['response_time'] else "-"
        
        table.append([
            check['timestamp'],
            f"{status_icon} {check['name']}",
            check['status'],
            check['status_code'] or '-',
            response_time,
            check['error_message'] or '-'
        ])
    
    print(tabulate(table, headers=['Time', 'Target', 'Status', 'Code', 'Time', 'Error']))
    print()


def show_stats():
    """Show overall statistics"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Uptime stats (last 24 hours)
    cursor.execute("""
        SELECT 
            t.name,
            COUNT(*) as total_checks,
            SUM(CASE WHEN c.status = 'success' THEN 1 ELSE 0 END) as successful,
            AVG(CASE WHEN c.status = 'success' THEN c.response_time ELSE NULL END) as avg_response
        FROM checks c
        JOIN targets t ON c.target_id = t.id
        WHERE c.timestamp > datetime('now', '-24 hours')
        GROUP BY t.id, t.name
    """)
    
    stats = cursor.fetchall()
    
    print("\n📈 24-Hour Statistics:\n")
    
    table = []
    for stat in stats:
        uptime = (stat['successful'] / stat['total_checks'] * 100) if stat['total_checks'] > 0 else 0
        avg_ms = f"{stat['avg_response']:.0f}ms" if stat['avg_response'] else "-"
        
        table.append([
            stat['name'],
            f"{uptime:.1f}%",
            f"{stat['successful']}/{stat['total_checks']}",
            avg_ms
        ])
    
    print(tabulate(table, headers=['Target', 'Uptime', 'Success/Total', 'Avg Response']))
    print()


def main():
    if not DB_PATH.exists():
        print("❌ Database not found. Run 'python3 watchdog.py init' first.")
        sys.exit(1)
    
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if command == "incidents":
        show_incidents()
    elif command == "checks":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_recent_checks(limit)
    elif command == "stats":
        show_stats()
    elif command == "all":
        show_incidents()
        show_stats()
        show_recent_checks(10)
    else:
        print("Usage: status.py [all|incidents|checks|stats]")
        sys.exit(1)


if __name__ == "__main__":
    main()
