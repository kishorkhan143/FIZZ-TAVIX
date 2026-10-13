# SSH Event Collector for TAVIX GUARD

This module monitors SSH authentication events on your laptop and sends them to the TAVIX GUARD dashboard in real time.

## What It Does

- **Monitors SSH logins** - Captures successful and failed SSH authentication attempts
- **Detects brute-force attacks** - Alerts when multiple failed login attempts occur from one IP
- **Sends to dashboard** - Forwards all events to the backend for real-time visualization
- **Cross-platform** - Works on Windows (with OpenSSH), Linux, and macOS

## Supported Events

| Event Type | Description | Risk Level |
|---|---|---|
| **LOGIN-OK** | Successful SSH login | Low |
| **LOGIN-FAIL** | Failed SSH authentication attempt | Medium |
| **INVALID-USER** | Attempt with non-existent username | Medium |
| **BRUTE-FORCE** | Multiple failures from same IP in short time | High |

## Installation

### Prerequisites

- Python 3.7+
- pip package manager

### On Windows (with OpenSSH Server)

```powershell
# Install OpenSSH Server (if not already installed)
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd

# Install Python dependencies
pip install -r requirements.txt
```

### On Linux

```bash
# Ensure SSH server is running
sudo systemctl start ssh

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### Option 1: Automatic Script (Windows)

```batch
start_ssh_collector.bat http://192.168.1.100:8000 LAPTOP-A
```

### Option 2: Manual Python Command

```bash
python collector_with_ssh.py --backend http://192.168.1.100:8000 --label LAPTOP-A
```

### Option 3: Standalone SSH Monitor (testing only)

```bash
python ssh_monitor.py
```

## Configuration

### Environment Variables

Set these before running the collector:

```bash
# Set the collector secret (must match backend config)
export AS_COLLECTOR_SECRET=authsentinel-lab-secret-2026

# Set brute-force detection parameters
export SSH_MAX_FAILURES=5
export SSH_WINDOW_SECONDS=60
```

### Command-Line Arguments

```
--backend URL      Backend API URL (default: http://localhost:8000)
--label NAME       Machine label to report to backend (default: LAPTOP-A)
--threshold N      Failed attempts before brute-force alert (default: 5)
--window N         Brute-force sliding window in seconds (default: 60)
```

## How It Works

1. **Connects to backend**: Verifies connectivity to AuthSentinel backend
2. **Monitors SSH logs**: Reads SSH authentication events from:
   - Windows: OpenSSH/Operational Event Log
   - Linux: `/var/log/auth.log` or `journalctl`
3. **Parses events**: Extracts username, source IP, timestamp, and status
4. **Sends to dashboard**: POSTs events to `/api/events` endpoint
5. **Detects patterns**: Tracks multiple failures from single IP for brute-force detection

## Event Format Sent to Backend

```json
{
  "event_id": 9999,
  "timestamp": "2024-10-13T15:30:45.123456+00:00",
  "username": "admin",
  "source_ip": "192.168.1.100",
  "source_host": "192.168.1.100",
  "target_computer": "LAPTOP-A",
  "logon_type": "RemoteInteractive",
  "logon_type_description": "SSH Remote Login",
  "status": "SUCCESS",
  "alert_type": "SUCCESSFUL_LOGIN",
  "risk_level": "LOW",
  "reason": "SSH LOGIN-OK: password authentication"
}
```

## Troubleshooting

### "Backend unavailable" Error

Make sure the backend is running:
```bash
# Check backend is listening
curl http://192.168.1.100:8000/api/health
```

### "Permission denied" Error (Linux)

SSH log monitoring requires root or group membership:
```bash
sudo python collector_with_ssh.py
# OR
sudo usermod -a -G adm,systemd-journal $USER
logout  # Then log back in
```

### "Invalid collector secret" Error

Ensure the backend and collector are configured with the same secret:
- Backend: Check `AS_COLLECTOR_SECRET` in `.env`
- Collector: Set before running or pass in environment

### No SSH Events Detected

1. Check SSH server is running:
   ```bash
   sudo systemctl status ssh    # Linux
   Get-Service sshd             # Windows (PowerShell)
   ```

2. Make an SSH connection to test:
   ```bash
   ssh user@localhost
   ssh -p 22 user@127.0.0.1
   ```

3. Verify log file exists:
   ```bash
   cat /var/log/auth.log | grep sshd  # Linux
   ```

## Dashboard Integration

Once events are sent to the backend, they appear in:

1. **Events View** - All SSH authentication events
2. **Alerts View** - High-risk events (brute-force, invalid users)
3. **Live Dashboard** - Real-time graphs and statistics
4. **Timeline** - Chronological event history

## Security Notes

- ✅ **No passwords transmitted** - Only metadata (username, IP, timestamp)
- ✅ **HTTPS ready** - Works with encrypted connections
- ✅ **Collector secret** - Authentication between collector and backend
- ✅ **Event source** - All events tagged with source machine label

## Performance

- **Memory**: ~10-15 MB baseline
- **CPU**: <1% when idle
- **Network**: ~1 KB per event (< 100 bytes typical)
- **Latency**: Events forwarded within 1-2 seconds of SSH log entry

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: `tail -f /var/log/authsentinel.log`
3. Check collector logs in terminal output
4. Verify network connectivity between machines

---

**TAVIX GUARD SSH Event Collector** | Real-time security monitoring for SSH authentication
