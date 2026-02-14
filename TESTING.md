# Testing Guide

## Test Suite Overview

Comprehensive test coverage for Website Watchdog with **30 test cases** covering:

- ✅ **Database operations** (9 tests)
- ✅ **HTTP checking logic** (6 tests)
- ✅ **Incident management** (3 tests)
- ✅ **Alert handling** (4 tests)
- ✅ **End-to-end integration** (2 tests)
- ✅ **Edge cases** (6 tests)

## Quick Start

```bash
# Run all tests
./run_tests.sh

# Or manually:
cd ~/work/website_watchdog
source venv/bin/activate
pytest test_watchdog.py -v
```

## Test Coverage

Current coverage: **~56%** overall

- `watchdog.py`: 83% (core monitoring logic)
- `alerter.py`: 53% (alert routing)
- `status.py`: 0% (display-only, not critical)

Untested sections are mainly:
- SMTP email sending (integration with external service)
- SMS sending via Twilio/email gateway
- Command-line parsing and main() functions

## Test Categories

### Database Tests (`TestWatchdogDB`)

- Schema initialization
- Loading targets from config
- Recording check results
- Creating and managing incidents
- Marking alerts as sent

### HTTP Checking Tests (`TestWatchdogChecking`)

- Successful health checks
- Wrong status codes
- Timeouts
- Connection errors
- Content validation (success and failure)

### Incident Management Tests (`TestIncidentManagement`)

- First failure creates incident
- Consecutive failures increment count
- Recovery resolves incident

### Alerter Tests (`TestAlerter`)

- Message formatting
- Slack notifications
- Email notifications
- Escalation thresholds

### Integration Tests (`TestIntegration`)

- Full failure → escalation → recovery cycle
- Multiple independent targets

### Edge Cases (`TestEdgeCases`)

- Empty database
- Disabled targets
- Very slow responses
- Malformed config
- Concurrent incidents

## Running Specific Tests

```bash
# Run one test class
pytest test_watchdog.py::TestWatchdogDB -v

# Run one specific test
pytest test_watchdog.py::TestWatchdogDB::test_init_schema -v

# Run with coverage report
pytest test_watchdog.py --cov=. --cov-report=html

# Run only fast tests (exclude slow/network)
pytest test_watchdog.py -m "not slow" -v
```

## Test Fixtures

### `temp_db`
Creates temporary SQLite database for each test.
Automatically cleaned up after test completes.

### `temp_config`
Creates temporary YAML config with test targets.
Includes sample alert configuration.

### `mock_requests`
Mocks the `requests` library for HTTP testing.
No actual network calls during tests.

### `mock_alerter`
Mocks alert sending for watchdog testing.
Verifies alert logic without sending real alerts.

## Writing New Tests

### Example: Test a new feature

```python
def test_new_feature(temp_db, temp_config):
    """Test description"""
    # Arrange
    temp_db.load_targets_from_config(temp_config)
    watchdog = Watchdog(temp_db.db_path, temp_config)
    
    # Act
    result = watchdog.some_method()
    
    # Assert
    assert result['status'] == 'expected_value'
```

### Best Practices

1. **Use fixtures** - Don't create databases manually
2. **Mock external calls** - No real HTTP/SMTP/Slack
3. **Test edge cases** - Empty inputs, errors, timeouts
4. **Clear names** - `test_check_target_timeout` not `test1`
5. **One assertion per concept** - Don't test 5 things at once

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request

See `.github/workflows/test.yml` for CI configuration.

## Debugging Failed Tests

```bash
# Show full traceback
pytest test_watchdog.py -v --tb=long

# Stop at first failure
pytest test_watchdog.py -x

# Drop into debugger on failure
pytest test_watchdog.py --pdb

# Show print statements
pytest test_watchdog.py -s
```

## Coverage Reports

After running tests, view HTML coverage report:

```bash
open coverage_html/index.html
```

This shows exactly which lines are covered/uncovered.

## Performance

Test suite runs in **<1 second** ⚡

All tests use in-memory databases and mocked HTTP calls.
No external dependencies = fast and reliable.

## Test Data

Sample targets used in tests:
- `Test Service`: https://example.com/api/health
- `Slow Service`: https://slow.example.com

Sample alert config:
- Slack: #test-alerts
- Email: test@example.com
- SMS: +15551234567

## Mocking Strategy

We mock at the boundary:
- `requests.request()` - No actual HTTP calls
- `subprocess.run()` - No actual Clawdbot calls
- `smtplib.SMTP()` - No actual emails sent

This keeps tests:
- **Fast** - No network I/O
- **Reliable** - No external dependencies
- **Isolated** - Tests don't affect real systems

## Common Issues

### "ModuleNotFoundError: No module named 'pytest'"

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Database is locked"

Tests create isolated temp databases. If you see this, a test didn't clean up properly.

### "AssertionError in test_send_slack"

Make sure mock is returning the right values. Check `mock_run.call_args`.

## Next Steps

To increase coverage:

1. **Add integration tests** for SMTP (use test mail server)
2. **Add integration tests** for Slack (use test workspace)
3. **Test CLI commands** (`watchdog.py init`, etc.)
4. **Test status.py** display logic
5. **Add performance benchmarks** (how many checks/second?)

## Questions?

- Check test output: `pytest test_watchdog.py -v`
- Read the test code: It's well-commented
- Ask the team: Tests are documentation too!
