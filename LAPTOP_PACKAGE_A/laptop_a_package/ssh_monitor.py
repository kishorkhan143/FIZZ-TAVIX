#!/usr/bin/env python3
"""
SSH Login Monitor
-----------------
Watches SSH auth logs in real time and alerts on:
  - Successful logins (LOGIN-OK)
  - Failed password / key attempts (LOGIN-FAIL)
  - Invalid (non-existent) usernames (INVALID-USER)
  - Brute-force behaviour (many failures from one IP in a short time)

Supports both Linux (/var/log/auth.log, journalctl) and Windows (OpenSSH/Operational Event Log).
"""

import argparse
import os
import queue
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional, Tuple, Generator

# Enable ANSI terminal colors and UTF-8 output on Windows console
if sys.platform == "win32":
    os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ────────────────── Settings ──────────────────
LINUX_LOG_CANDIDATES = ["/var/log/auth.log", "/var/log/secure"]
ALERT_LOG = "ssh_alerts.log"       # Alerts are appended here
MAX_FAILURES = 5                   # Failures allowed...
WINDOW_SECONDS = 60                # ...within this many seconds before "brute force" alert
# ──────────────────────────────────────────────

# Regex patterns for sshd log lines
RE_FAILED = re.compile(r"Failed (\w+) for (invalid user )?(\S+) from (\S+) port (\d+)")
RE_INVALID = re.compile(r"Invalid user (\S*) from (\S+)")
RE_ACCEPTED = re.compile(r"Accepted (\w+) for (\S+) from (\S+) port (\d+)")

failures = defaultdict(deque)      # ip -> timestamps of recent failures
brute_alerted = {}                 # ip -> last time brute-force alert was sent

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class SSHEvent:
    """Represents a parsed SSH authentication event."""
    def __init__(self, event_type: str, username: str, source_ip: str, port: str, 
                 method: str = "", timestamp: Optional[str] = None, is_invalid_user: bool = False):
        self.event_type = event_type  # "LOGIN-OK", "LOGIN-FAIL", "INVALID-USER", "BRUTE-FORCE"
        self.username = username
        self.source_ip = source_ip
        self.port = port
        self.method = method
        self.timestamp = timestamp or datetime.now().isoformat()
        self.is_invalid_user = is_invalid_user

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "username": self.username,
            "source_ip": self.source_ip,
            "port": self.port,
            "method": self.method,
            "timestamp": self.timestamp,
            "is_invalid_user": self.is_invalid_user,
        }

    def __str__(self):
        return f"[{self.event_type}] {self.username}@{self.source_ip}:{self.port} ({self.method})"


def alert(level, message, color, timestamp=None, save_to_log=True):
    """Print an alert and append it to the alert log file."""
    stamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] [{level}] {message}"
    print(f"{color}{line}{RESET}", flush=True)
    if save_to_log:
        try:
            with open(ALERT_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[!] Warning: Could not write to {ALERT_LOG}: {e}", file=sys.stderr)


def record_failure(ip, event_time=None, max_failures=MAX_FAILURES, window_seconds=WINDOW_SECONDS, save_to_log=True):
    """Track failures per IP and raise a brute-force alert if threshold is exceeded."""
    now = event_time if event_time is not None else time.time()
    q = failures[ip]
    q.append(now)
    while q and (now - q[0]) > window_seconds:
        q.popleft()
    if len(q) >= max_failures and (now - brute_alerted.get(ip, 0)) > window_seconds:
        brute_alerted[ip] = now
        alert(
            "SSH DETECTED: FAILED (BRUTE-FORCE)",
            f"{ip} made {len(q)} failed attempts in {window_seconds}s",
            RED,
            timestamp=datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S") if event_time else None,
            save_to_log=save_to_log,
        )
        return True
    return False


def process(line, timestamp=None, max_failures=MAX_FAILURES, window_seconds=WINDOW_SECONDS, 
            event_epoch=None, save_to_log=True) -> Optional[SSHEvent]:
    """Parse an SSH log line and trigger alerts. Returns SSHEvent if detected."""
    
    # Check for successful login
    m = RE_ACCEPTED.search(line)
    if m:
        method, user, ip, port = m.groups()
        alert("SSH DETECTED: SUCCESS", f"user '{user}' logged in from {ip}:{port} using {method}", 
              GREEN, timestamp=timestamp, save_to_log=save_to_log)
        return SSHEvent(
            event_type="LOGIN-OK",
            username=user,
            source_ip=ip,
            port=port,
            method=method,
            timestamp=timestamp
        )

    # Check for failed login attempt
    m = RE_FAILED.search(line)
    if m:
        method, invalid, user, ip, port = m.groups()
        tag = " (invalid user)" if invalid else ""
        alert("SSH DETECTED: FAILED", f"failed {method} for '{user}'{tag} from {ip}:{port}", 
              RED, timestamp=timestamp, save_to_log=save_to_log)
        record_failure(ip, event_time=event_epoch, max_failures=max_failures, 
                      window_seconds=window_seconds, save_to_log=save_to_log)
        return SSHEvent(
            event_type="LOGIN-FAIL",
            username=user,
            source_ip=ip,
            port=port,
            method=method,
            timestamp=timestamp,
            is_invalid_user=bool(invalid)
        )

    # Check for invalid user
    m = RE_INVALID.search(line)
    if m:
        user, ip = m.groups()
        alert("SSH DETECTED: FAILED", f"attempt with non-existent user '{user}' from {ip}", 
              YELLOW, timestamp=timestamp, save_to_log=save_to_log)
        record_failure(ip, event_time=event_epoch, max_failures=max_failures, 
                      window_seconds=window_seconds, save_to_log=save_to_log)
        return SSHEvent(
            event_type="INVALID-USER",
            username=user,
            source_ip=ip,
            port="",
            timestamp=timestamp,
            is_invalid_user=True
        )

    return None


# ────────────── Windows Event Log Support ──────────────

def parse_event_xml(xml_str):
    """Extract local timestamp, unix epoch, and payload from Windows Event Log XML."""
    try:
        root = ET.fromstring(xml_str)
    except Exception:
        return None, None, None

    ts_str, epoch, payload = None, None, None
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "TimeCreated" and "SystemTime" in elem.attrib:
            raw_time = elem.attrib["SystemTime"]
            try:
                dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                epoch = dt.timestamp()
                ts_str = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_str = raw_time
        elif tag == "Data" and elem.attrib.get("Name") == "payload":
            payload = elem.text

    return ts_str, epoch, payload


def get_windows_history(channel="OpenSSH/Operational", max_events=20):
    """Retrieve the most recent historical events from Windows Event Log."""
    try:
        import win32evtlog
        query_handle = win32evtlog.EvtQuery(
            channel,
            win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection,
        )
        events = win32evtlog.EvtNext(query_handle, max_events)
        results = []
        for e in reversed(events):
            xml_data = win32evtlog.EvtRender(e, win32evtlog.EvtRenderEventXml)
            ts, epoch, payload = parse_event_xml(xml_data)
            if payload:
                results.append((ts, epoch, payload))
        return results
    except Exception as e:
        print(f"[*] Could not read history via win32evtlog: {e}")
        return []


def follow_windows_events(channel="OpenSSH/Operational") -> Generator[Tuple[Optional[str], Optional[float], str], None, None]:
    """Live generator for Windows OpenSSH event log using EvtSubscribe."""
    try:
        import win32evtlog
    except ImportError:
        print("[!] pywin32 is required for Windows live monitoring (install via `pip install pywin32`)")
        return

    event_q = queue.Queue()

    def callback(action, context, handle):
        if action == win32evtlog.EvtSubscribeActionDeliver:
            try:
                xml_data = win32evtlog.EvtRender(handle, win32evtlog.EvtRenderEventXml)
                event_q.put(xml_data)
            except Exception:
                pass

    try:
        _sub = win32evtlog.EvtSubscribe(
            channel,
            win32evtlog.EvtSubscribeToFutureEvents,
            Callback=callback,
        )
    except Exception as e:
        print(f"[!] Failed to subscribe to {channel}: {e}")
        print("[*] Tip: Ensure OpenSSH Server is installed and the service is started.")
        return

    while True:
        try:
            xml_data = event_q.get(timeout=0.5)
            ts, epoch, payload = parse_event_xml(xml_data)
            if payload:
                yield (ts, epoch, payload)
        except queue.Empty:
            continue


# ────────────── Linux / File Support ──────────────

def follow_file(path) -> Generator[Tuple[None, None, str], None, None]:
    """Yield new lines appended to a file (like `tail -f`)."""
    f = open(path, "r", errors="ignore")
    f.seek(0, os.SEEK_END)
    inode = os.fstat(f.fileno()).st_ino
    while True:
        line = f.readline()
        if line:
            yield (None, None, line.strip())
            continue
        time.sleep(0.5)
        try:
            if os.stat(path).st_ino != inode:   # File was rotated
                f.close()
                f = open(path, "r", errors="ignore")
                inode = os.fstat(f.fileno()).st_ino
        except FileNotFoundError:
            pass


def follow_journal() -> Generator[Tuple[None, None, str], None, None]:
    """Fallback for Linux systems without an auth log file (uses systemd journal)."""
    cmd = ["journalctl", "-f", "-n", "0", "-t", "sshd", "-t", "sshd-session", "-o", "short"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="ignore")
    for line in proc.stdout:
        yield (None, None, line.strip())


def get_ssh_events(max_failures=MAX_FAILURES, window_seconds=WINDOW_SECONDS) -> Generator[SSHEvent, None, None]:
    """Main dispatcher: yields SSH events from the appropriate source."""
    
    # Determine source
    if sys.platform == "win32":
        channel = "OpenSSH/Operational"
        print(f"[SSH Monitor] Windows platform detected. Monitoring: {channel}")
        source = follow_windows_events(channel=channel)
    else:
        found_file = None
        for path in LINUX_LOG_CANDIDATES:
            if os.path.exists(path):
                found_file = path
                break
        
        if found_file:
            print(f"[SSH Monitor] Linux auth log found: {found_file}")
            source = follow_file(found_file)
        else:
            print("[SSH Monitor] No auth log file found, falling back to journalctl")
            source = follow_journal()

    # Process events
    for item in source:
        ts, epoch, line = item
        event = process(line, timestamp=ts, max_failures=max_failures, 
                       window_seconds=window_seconds, event_epoch=epoch, save_to_log=False)
        if event:
            yield event
