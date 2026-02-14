# Service Management

Website Watchdog runs as a macOS LaunchAgent service for reliable, automated monitoring.

## Why Service Instead of Cron?

**LaunchAgent Benefits:**
- ✅ Auto-starts on login/boot
- ✅ Better logging (stdout + stderr separate)
- ✅ Automatic restart on failure
- ✅ Easier to start/stop/status
- ✅ Standard macOS service management

**Cron Drawbacks:**
- ❌ Doesn't auto-start on boot
- ❌ Limited logging
- ❌ No failure recovery
- ❌ Harder to debug

## Installation

```bash
cd ~/work/website_watchdog
./install_service.sh
```

This will:
1. Create Python virtual environment (if needed)
2. Initialize database (if needed)
3. Install LaunchAgent configuration
4. Start the service
5. Enable auto-start on login

## Service Commands

### Check Status
```bash
./service_status.sh
```

Or manually:
```bash
launchctl list | grep watchdog
```

### Stop Service
```bash
./uninstall_service.sh
```

Or manually:
```bash
launchctl unload ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
```

### Start Service (After Stop)
```bash
launchctl load ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
```

### Restart Service
```bash
launchctl unload ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
launchctl load ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
```

### Force Run Now (Don't Wait for Interval)
```bash
launchctl start com.cortadogroup.watchdog
```

## Logs

Service logs go to dedicated files:

- **Output**: `logs/service.log`
- **Errors**: `logs/service_error.log`

View live logs:
```bash
tail -f logs/service.log
tail -f logs/service_error.log
```

View recent checks:
```bash
python3 status.py checks 20
```

## Service Configuration

File: `~/Library/LaunchAgents/com.cortadogroup.watchdog.plist`

Key settings:
- **Interval**: 300 seconds (5 minutes)
- **Auto-start**: Yes (RunAtLoad)
- **Keep alive**: No (runs then exits)
- **Working directory**: Project root
- **Python**: Uses venv python

## Troubleshooting

### Service Won't Start

```bash
# Check plist syntax
plutil -lint ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist

# Check error log
cat logs/service_error.log

# Try manual run
source venv/bin/activate
python3 watchdog.py check
```

### Service Running But No Checks

```bash
# Check last run time
./service_status.sh

# Verify database
ls -lh db/watchdog.db

# Check targets configured
cat config/targets.yaml
```

### Logs Not Updating

```bash
# Check log permissions
ls -l logs/

# Create logs directory if missing
mkdir -p logs

# Restart service
launchctl unload ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
launchctl load ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
```

### Database Locked

```bash
# Stop service first
./uninstall_service.sh

# Check for stale locks
lsof db/watchdog.db

# Restart service
./install_service.sh
```

## Monitoring the Monitor

The watchdog monitors your services. Here's how to monitor the watchdog:

### Check Last Run
```bash
# View recent logs
tail -20 logs/service.log

# Check database timestamps
python3 status.py checks 5
```

### Alert on Watchdog Failure

Add a second-level monitor (external service like UptimeRobot) to check:
- `https://your-domain.com/watchdog-heartbeat` endpoint
- Or use macOS native notifications via launchd

### Database Size
```bash
# Monitor database growth
du -h db/watchdog.db
```

Database grows ~1KB per check. With 5-minute intervals:
- Daily: ~288 checks × 1KB = ~288KB/day
- Monthly: ~8.6MB/month
- Yearly: ~100MB/year

Set up rotation if needed.

## Uninstall

```bash
# Stop and remove service
./uninstall_service.sh

# Optionally remove all data
rm -rf ~/work/website_watchdog
```

## Migration from Cron

If you have an existing cron job:

```bash
# Remove cron job
crontab -e
# Delete the watchdog line

# Install service
./install_service.sh
```

The service uses the same database, so history is preserved.

## Advanced Configuration

### Change Check Interval

Edit `com.cortadogroup.watchdog.plist`:

```xml
<key>StartInterval</key>
<integer>60</integer>  <!-- 1 minute -->
```

Or for specific times:

```xml
<!-- Remove StartInterval, add: -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
launchctl load ~/Library/LaunchAgents/com.cortadogroup.watchdog.plist
```

### Run on Boot (System-wide)

Move to LaunchDaemons instead:

```bash
sudo cp com.cortadogroup.watchdog.plist /Library/LaunchDaemons/
sudo launchctl load /Library/LaunchDaemons/com.cortadogroup.watchdog.plist
```

**Note:** Update paths in plist to use absolute paths, not `~`.

### Environment Variables

Add to plist under `<key>EnvironmentVariables</key>`:

```xml
<key>SLACK_CHANNEL</key>
<string>#custom-alerts</string>
```

Or use `.env` file (already supported).

## Best Practices

1. **Monitor the logs** - Set up weekly review
2. **Test alerts** - Manually trigger failures occasionally
3. **Backup database** - Include in your backup routine
4. **Update targets** - Review monitored endpoints monthly
5. **Rotate logs** - Archive old logs periodically

## FAQ

**Q: Does it run when my Mac is asleep?**  
A: No. LaunchAgents only run when you're logged in and Mac is awake. For 24/7 monitoring, deploy to a server.

**Q: Can I run multiple instances?**  
A: Yes, but change the Label in the plist to make it unique.

**Q: How much CPU/memory does it use?**  
A: Minimal. Runs for ~1-2 seconds every 5 minutes. ~10MB memory during execution.

**Q: Can I monitor HTTPS with custom certs?**  
A: Yes. Python requests uses system cert store by default.

**Q: What happens if check takes longer than 5 minutes?**  
A: Next check waits until current one completes (KeepAlive=false).

---

For more details, see:
- `README.md` - Full documentation
- `QUICKSTART.md` - Setup guide
- `TESTING.md` - Test suite info
