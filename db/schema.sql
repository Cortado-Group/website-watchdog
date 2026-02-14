-- Website Watchdog Database Schema

-- Monitoring targets
CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    method TEXT DEFAULT 'GET',
    expected_status INTEGER DEFAULT 200,
    timeout INTEGER DEFAULT 10,
    contains TEXT,  -- Optional content validation
    enabled BOOLEAN DEFAULT 1,
    alert_channels TEXT,  -- JSON array: ["slack", "email", "sms"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Check history
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,  -- 'success', 'failure', 'timeout', 'error'
    status_code INTEGER,
    response_time REAL,  -- milliseconds
    error_message TEXT,
    FOREIGN KEY (target_id) REFERENCES targets(id)
);

-- Incidents (failures requiring attention)
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    status TEXT DEFAULT 'open',  -- 'open', 'resolved', 'acknowledged'
    failure_count INTEGER DEFAULT 1,
    last_check_id INTEGER,
    slack_alerted BOOLEAN DEFAULT 0,
    email_alerted BOOLEAN DEFAULT 0,
    sms_alerted BOOLEAN DEFAULT 0,
    FOREIGN KEY (target_id) REFERENCES targets(id),
    FOREIGN KEY (last_check_id) REFERENCES checks(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_checks_target_timestamp ON checks(target_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status, target_id);
CREATE INDEX IF NOT EXISTS idx_targets_enabled ON targets(enabled);
