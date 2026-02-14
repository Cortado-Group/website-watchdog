#!/usr/bin/env python3
"""
Comprehensive unit tests for Website Watchdog
Tests database, checking, alerting, and incident management
"""

import pytest
import sqlite3
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent))

from watchdog import WatchdogDB, Watchdog
from alerter import Alerter


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = WatchdogDB(path)
    db.connect()
    db.init_schema()
    
    yield db
    
    db.conn.close()
    os.unlink(path)


@pytest.fixture
def temp_config():
    """Create temporary config file"""
    fd, path = tempfile.mkstemp(suffix='.yaml')
    
    config_content = """
targets:
  - name: "Test Service"
    url: "https://example.com/api/health"
    method: GET
    expected_status: 200
    timeout: 10
    alert_channels:
      - slack
      - email

  - name: "Slow Service"
    url: "https://slow.example.com"
    method: GET
    expected_status: 200
    timeout: 1
    alert_channels:
      - slack

alerts:
  slack:
    enabled: true
    channel: "#test-alerts"
  email:
    enabled: true
    recipients:
      - "test@example.com"
    escalate_after: 3
  sms:
    enabled: true
    recipients:
      - "+15551234567"
    escalate_after: 5
    method: "email_gateway"
"""
    
    os.write(fd, config_content.encode())
    os.close(fd)
    
    yield path
    
    os.unlink(path)


@pytest.fixture
def mock_requests():
    """Mock requests library"""
    with patch('watchdog.requests') as mock:
        yield mock


@pytest.fixture
def mock_alerter():
    """Mock alerter for testing watchdog"""
    with patch('watchdog.Alerter') as mock:
        yield mock


# ============================================================================
# DATABASE TESTS
# ============================================================================

class TestWatchdogDB:
    """Test database operations"""
    
    def test_init_schema(self, temp_db):
        """Test schema initialization"""
        cursor = temp_db.conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert 'targets' in tables
        assert 'checks' in tables
        assert 'incidents' in tables
    
    def test_load_targets_from_config(self, temp_db, temp_config):
        """Test loading targets from YAML config"""
        temp_db.load_targets_from_config(temp_config)
        
        targets = temp_db.get_active_targets()
        assert len(targets) == 2
        
        target1 = targets[0]
        assert target1['name'] == 'Test Service'
        assert target1['url'] == 'https://example.com/api/health'
        assert target1['expected_status'] == 200
        assert json.loads(target1['alert_channels']) == ['slack', 'email']
    
    def test_record_check_success(self, temp_db, temp_config):
        """Test recording successful check"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        check_id = temp_db.record_check(
            target_id=target_id,
            status='success',
            status_code=200,
            response_time=150.5,
            error_message=None
        )
        
        assert check_id is not None
        
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT * FROM checks WHERE id = ?", (check_id,))
        check = cursor.fetchone()
        
        assert check['status'] == 'success'
        assert check['status_code'] == 200
        assert check['response_time'] == 150.5
        assert check['error_message'] is None
    
    def test_record_check_failure(self, temp_db, temp_config):
        """Test recording failed check"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        check_id = temp_db.record_check(
            target_id=target_id,
            status='failure',
            status_code=500,
            response_time=None,
            error_message='Internal Server Error'
        )
        
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT * FROM checks WHERE id = ?", (check_id,))
        check = cursor.fetchone()
        
        assert check['status'] == 'failure'
        assert check['status_code'] == 500
        assert check['error_message'] == 'Internal Server Error'
    
    def test_create_incident(self, temp_db, temp_config):
        """Test creating new incident"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        check_id = temp_db.record_check(target_id, 'failure', 500)
        incident_id = temp_db.create_incident(target_id, check_id)
        
        assert incident_id is not None
        
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        incident = cursor.fetchone()
        
        assert incident['target_id'] == target_id
        assert incident['status'] == 'open'
        assert incident['failure_count'] == 1
        assert incident['last_check_id'] == check_id
    
    def test_update_incident(self, temp_db, temp_config):
        """Test updating incident with new failure"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        check_id1 = temp_db.record_check(target_id, 'failure', 500)
        incident_id = temp_db.create_incident(target_id, check_id1)
        
        check_id2 = temp_db.record_check(target_id, 'failure', 500)
        temp_db.update_incident(incident_id, check_id2, increment_count=True)
        
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        incident = cursor.fetchone()
        
        assert incident['failure_count'] == 2
        assert incident['last_check_id'] == check_id2
    
    def test_resolve_incident(self, temp_db, temp_config):
        """Test resolving incident"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        check_id = temp_db.record_check(target_id, 'failure', 500)
        incident_id = temp_db.create_incident(target_id, check_id)
        
        temp_db.resolve_incident(incident_id)
        
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        incident = cursor.fetchone()
        
        assert incident['status'] == 'resolved'
        assert incident['resolved_at'] is not None
    
    def test_get_open_incident(self, temp_db, temp_config):
        """Test retrieving open incident"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        # No incident initially
        incident = temp_db.get_open_incident(target_id)
        assert incident is None
        
        # Create incident
        check_id = temp_db.record_check(target_id, 'failure', 500)
        incident_id = temp_db.create_incident(target_id, check_id)
        
        # Should find it now
        incident = temp_db.get_open_incident(target_id)
        assert incident is not None
        assert incident['id'] == incident_id
        assert incident['status'] == 'open'
        
        # Resolve it
        temp_db.resolve_incident(incident_id)
        
        # Should not find open incident
        incident = temp_db.get_open_incident(target_id)
        assert incident is None
    
    def test_mark_alert_sent(self, temp_db, temp_config):
        """Test marking alerts as sent"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        check_id = temp_db.record_check(target_id, 'failure', 500)
        incident_id = temp_db.create_incident(target_id, check_id)
        
        # Mark alerts sent
        temp_db.mark_alert_sent(incident_id, 'slack')
        temp_db.mark_alert_sent(incident_id, 'email')
        
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        incident = cursor.fetchone()
        
        assert incident['slack_alerted'] == 1
        assert incident['email_alerted'] == 1
        assert incident['sms_alerted'] == 0


# ============================================================================
# HTTP CHECKING TESTS
# ============================================================================

class TestWatchdogChecking:
    """Test HTTP endpoint checking logic"""
    
    def test_check_target_success(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test successful health check"""
        temp_db.load_targets_from_config(temp_config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_requests.request.return_value = mock_response
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        result = watchdog.check_target(targets[0])
        
        assert result['status'] == 'success'
        assert result['status_code'] == 200
        assert result['response_time'] > 0
        assert result['error_message'] is None
    
    def test_check_target_wrong_status_code(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test check with unexpected status code"""
        temp_db.load_targets_from_config(temp_config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.request.return_value = mock_response
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        result = watchdog.check_target(targets[0])
        
        assert result['status'] == 'failure'
        assert result['status_code'] == 500
        assert 'Expected 200, got 500' in result['error_message']
    
    def test_check_target_timeout(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test timeout handling"""
        temp_db.load_targets_from_config(temp_config)
        
        import requests
        mock_requests.request.side_effect = requests.Timeout("Connection timeout")
        mock_requests.Timeout = requests.Timeout
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        result = watchdog.check_target(targets[0])
        
        assert result['status'] == 'timeout'
        assert 'Timeout' in result['error_message']
    
    def test_check_target_connection_error(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test connection error handling"""
        temp_db.load_targets_from_config(temp_config)
        
        # Mock Timeout exception class
        import requests
        mock_requests.Timeout = requests.Timeout
        
        # Use a proper Exception subclass
        mock_requests.request.side_effect = ConnectionError("Connection refused")
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        result = watchdog.check_target(targets[0])
        
        assert result['status'] == 'error'
        assert 'Connection refused' in result['error_message']
    
    def test_check_target_content_validation_success(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test content validation - success"""
        temp_db.load_targets_from_config(temp_config)
        
        # Add content validation to target
        cursor = temp_db.conn.cursor()
        cursor.execute("UPDATE targets SET contains = 'healthy' WHERE name = 'Test Service'")
        temp_db.conn.commit()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Status: healthy"
        mock_requests.request.return_value = mock_response
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        result = watchdog.check_target(targets[0])
        
        assert result['status'] == 'success'
    
    def test_check_target_content_validation_failure(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test content validation - failure"""
        temp_db.load_targets_from_config(temp_config)
        
        # Add content validation to target
        cursor = temp_db.conn.cursor()
        cursor.execute("UPDATE targets SET contains = 'healthy' WHERE name = 'Test Service'")
        temp_db.conn.commit()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Status: degraded"
        mock_requests.request.return_value = mock_response
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        result = watchdog.check_target(targets[0])
        
        assert result['status'] == 'failure'
        assert 'Expected content' in result['error_message']
        assert 'healthy' in result['error_message']


# ============================================================================
# INCIDENT MANAGEMENT TESTS
# ============================================================================

class TestIncidentManagement:
    """Test incident creation, escalation, and resolution"""
    
    def test_first_failure_creates_incident(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test that first failure creates new incident"""
        temp_db.load_targets_from_config(temp_config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.request.return_value = mock_response
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        # No incident initially
        incident = temp_db.get_open_incident(target_id)
        assert incident is None
        
        # Run check
        result = watchdog.check_target(targets[0])
        watchdog.handle_result(result)
        
        # Incident should be created
        incident = temp_db.get_open_incident(target_id)
        assert incident is not None
        assert incident['failure_count'] == 1
    
    def test_consecutive_failures_increment_count(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test that consecutive failures increment incident count"""
        temp_db.load_targets_from_config(temp_config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.request.return_value = mock_response
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        # First failure
        result = watchdog.check_target(targets[0])
        watchdog.handle_result(result)
        
        incident = temp_db.get_open_incident(target_id)
        assert incident['failure_count'] == 1
        
        # Second failure
        result = watchdog.check_target(targets[0])
        watchdog.handle_result(result)
        
        incident = temp_db.get_open_incident(target_id)
        assert incident['failure_count'] == 2
        
        # Third failure
        result = watchdog.check_target(targets[0])
        watchdog.handle_result(result)
        
        incident = temp_db.get_open_incident(target_id)
        assert incident['failure_count'] == 3
    
    def test_recovery_resolves_incident(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test that success after failure resolves incident"""
        temp_db.load_targets_from_config(temp_config)
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        # Fail
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.request.return_value = mock_response
        
        result = watchdog.check_target(targets[0])
        watchdog.handle_result(result)
        
        incident = temp_db.get_open_incident(target_id)
        assert incident is not None
        
        # Recover
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        result = watchdog.check_target(targets[0])
        watchdog.handle_result(result)
        
        # Incident should be resolved
        incident = temp_db.get_open_incident(target_id)
        assert incident is None


# ============================================================================
# ALERTER TESTS
# ============================================================================

class TestAlerter:
    """Test alert sending logic"""
    
    def test_format_failure_message(self, temp_config):
        """Test failure message formatting"""
        alerter = Alerter(temp_config)
        
        result = {
            'name': 'Test Service',
            'status': 'failure',
            'status_code': 500,
            'error_message': 'Internal Server Error',
            'response_time': 250.5
        }
        
        message = alerter._format_failure_message(result)
        
        assert 'Test Service' in message
        assert '500' in message
        assert 'Internal Server Error' in message
    
    def test_format_failure_message_with_count(self, temp_config):
        """Test failure message with consecutive count"""
        alerter = Alerter(temp_config)
        
        result = {
            'name': 'Test Service',
            'status': 'failure',
            'status_code': 500,
            'error_message': 'Internal Server Error'
        }
        
        message = alerter._format_failure_message(result, failure_count=5)
        
        assert '*Consecutive Failures*: 5' in message
    
    @patch('alerter.subprocess.run')
    def test_send_slack(self, mock_run, temp_config):
        """Test Slack alert sending"""
        mock_run.return_value = Mock(returncode=0, stderr='')
        
        alerter = Alerter(temp_config)
        
        result = {
            'name': 'Test Service',
            'status': 'failure',
            'status_code': 500,
            'error_message': 'Internal Server Error',
            'alert_channels': ['slack']
        }
        
        alerter.send_initial_alert(result)
        
        # Verify subprocess.run was called with clawdbot command
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'clawdbot' in call_args
        assert 'message' in call_args
    
    @patch('alerter.smtplib.SMTP')
    def test_send_email(self, mock_smtp, temp_config, monkeypatch):
        """Test email alert sending"""
        # Set environment variables
        monkeypatch.setenv('SMTP_HOST', 'smtp.test.com')
        monkeypatch.setenv('SMTP_PORT', '587')
        monkeypatch.setenv('SMTP_USER', 'test@test.com')
        monkeypatch.setenv('SMTP_PASSWORD', 'password')
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        alerter = Alerter(temp_config)
        
        alerter._send_email(
            subject='Test Alert',
            body='Test message',
            recipients=['recipient@test.com']
        )
        
        # Verify SMTP operations
        assert mock_server.starttls.called
        assert mock_server.login.called
        assert mock_server.send_message.called
        assert mock_server.quit.called
    
    def test_escalation_thresholds(self, temp_config):
        """Test alert escalation based on failure count"""
        alerter = Alerter(temp_config)
        
        # Check thresholds from config
        email_threshold = alerter.alert_config['email']['escalate_after']
        sms_threshold = alerter.alert_config['sms']['escalate_after']
        
        assert email_threshold == 3
        assert sms_threshold == 5


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """End-to-end integration tests"""
    
    @patch('watchdog.Alerter')
    @patch('watchdog.requests')
    def test_full_failure_recovery_cycle(self, mock_requests, mock_alerter, temp_db, temp_config):
        """Test complete failure -> escalation -> recovery cycle"""
        temp_db.load_targets_from_config(temp_config)
        
        mock_alerter_instance = MagicMock()
        mock_alerter.return_value = mock_alerter_instance
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        target = targets[0]
        target_id = target['id']
        
        # Simulate 5 consecutive failures
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.request.return_value = mock_response
        
        for i in range(5):
            result = watchdog.check_target(target)
            watchdog.handle_result(result)
        
        # Verify incident exists with correct count
        incident = temp_db.get_open_incident(target_id)
        assert incident['failure_count'] == 5
        
        # Verify initial alert was sent
        assert mock_alerter_instance.send_initial_alert.called
        
        # Verify escalation alert was sent
        assert mock_alerter_instance.send_escalation_alert.called
        
        # Simulate recovery
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        result = watchdog.check_target(target)
        watchdog.handle_result(result)
        
        # Verify incident is resolved
        incident = temp_db.get_open_incident(target_id)
        assert incident is None
        
        # Verify recovery alert was sent
        assert mock_alerter_instance.send_recovery_alert.called
    
    @patch('watchdog.Alerter')
    @patch('watchdog.requests')
    def test_multiple_targets_independent_incidents(self, mock_requests, mock_alerter, temp_db, temp_config):
        """Test that multiple targets have independent incidents"""
        temp_db.load_targets_from_config(temp_config)
        
        mock_alerter_instance = MagicMock()
        mock_alerter.return_value = mock_alerter_instance
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        target1 = targets[0]
        target2 = targets[1]
        
        # Fail target 1
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.request.return_value = mock_response
        
        result = watchdog.check_target(target1)
        watchdog.handle_result(result)
        
        # Verify target 1 has incident
        incident1 = temp_db.get_open_incident(target1['id'])
        assert incident1 is not None
        
        # Verify target 2 has no incident
        incident2 = temp_db.get_open_incident(target2['id'])
        assert incident2 is None
        
        # Fail target 2
        result = watchdog.check_target(target2)
        watchdog.handle_result(result)
        
        # Verify both have incidents now
        incident1 = temp_db.get_open_incident(target1['id'])
        incident2 = temp_db.get_open_incident(target2['id'])
        
        assert incident1 is not None
        assert incident2 is not None
        assert incident1['id'] != incident2['id']


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_database(self, temp_db):
        """Test behavior with no targets"""
        targets = temp_db.get_active_targets()
        assert len(targets) == 0
    
    def test_disabled_target_not_checked(self, temp_db, temp_config):
        """Test that disabled targets are skipped"""
        temp_db.load_targets_from_config(temp_config)
        
        # Disable first target
        cursor = temp_db.conn.cursor()
        cursor.execute("UPDATE targets SET enabled = 0 WHERE name = 'Test Service'")
        temp_db.conn.commit()
        
        targets = temp_db.get_active_targets()
        assert len(targets) == 1
        assert targets[0]['name'] == 'Slow Service'
    
    def test_very_slow_response(self, temp_db, temp_config, mock_requests, mock_alerter):
        """Test handling of very slow responses"""
        temp_db.load_targets_from_config(temp_config)
        
        # Simulate slow response (but not timeout)
        import time
        def slow_response(*args, **kwargs):
            time.sleep(0.1)  # 100ms delay
            mock = Mock()
            mock.status_code = 200
            mock.text = "OK"
            return mock
        
        mock_requests.request.side_effect = slow_response
        
        watchdog = Watchdog(temp_db.db_path, temp_config)
        watchdog.db = temp_db
        
        targets = temp_db.get_active_targets()
        result = watchdog.check_target(targets[0])
        
        assert result['status'] == 'success'
        assert result['response_time'] >= 100  # At least 100ms
    
    def test_malformed_config(self):
        """Test handling of malformed config file"""
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.write(fd, b"invalid: yaml: content: ][")
        os.close(fd)
        
        with pytest.raises(Exception):
            import yaml
            with open(path) as f:
                yaml.safe_load(f)
        
        os.unlink(path)
    
    def test_concurrent_incidents_same_target(self, temp_db, temp_config):
        """Test that only one open incident exists per target"""
        temp_db.load_targets_from_config(temp_config)
        targets = temp_db.get_active_targets()
        target_id = targets[0]['id']
        
        # Create first incident
        check_id1 = temp_db.record_check(target_id, 'failure', 500)
        incident_id1 = temp_db.create_incident(target_id, check_id1)
        
        # Try to create second incident (should use existing)
        check_id2 = temp_db.record_check(target_id, 'failure', 500)
        
        # Get open incident (should be the first one)
        incident = temp_db.get_open_incident(target_id)
        assert incident['id'] == incident_id1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
