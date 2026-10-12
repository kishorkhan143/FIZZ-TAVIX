"""
AuthSentinel — Universal Windows Event Collector
==================================================
Runs on EITHER Laptop A or Laptop B.

  Laptop B (monitor):  python collector.py
                       (backend defaults to localhost:8000)

  Laptop A (test):     python collector.py --backend http://192.168.x.10:8000 --label LAPTOP-A
                       (sends its own Security log to Laptop B's backend)

What it does
------------
- Polls the local Windows Security Event Log for Event IDs 4624 and 4625
- Parses ONLY security-event metadata — NEVER reads or transmits passwords
- POSTs parsed events to the AuthSentinel backend via HTTP
- Retries automatically if backend is unreachable
- Reports its hostname + IP so the dashboard can show which machine sent the event

Requirements (run once):
  pip install pywin32 requests python-dateutil colorama

Usage
-----
  python collector.py [--backend URL] [--label NAME] [--interval SECONDS (default: 0.1)]

Arguments:
  --backend   Backend URL  (default: http://127.0.0.1:8000)
  --label     Override the source label sent to the backend (default: hostname)
  --interval  Poll interval in seconds (default: 0.1 for near-real-time forwarding)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import socket
import logging
import threading
import platform
import ctypes
import getpass
import uuid
from urllib.parse import urlparse
from datetime import datetime, timezone
from typing import Optional

import requests
try:
    import win32evtlog
except ImportError:
    win32evtlog = None
from colorama import Fore, Style, init as colorama_init

# ── Console encoding fix for Windows ─────────────────────────────────────────
import io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

colorama_init(autoreset=True, convert=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)

# ── Constants ─────────────────────────────────────────────────────────────────
TARGET_EVENT_IDS   = {4624, 4625}
DUP_WINDOW_SECONDS = 3
COLLECTOR_SECRET   = os.environ.get("AS_COLLECTOR_SECRET", "authsentinel-lab-secret-2026")

LOGON_TYPES = {
    2: "Interactive",
    3: "Network",
    4: "Batch",
    5: "Service",
    7: "Unlock",
    8: "NetworkCleartext",
    9: "NewCredentials",
    10: "RemoteInteractive",
    11: "CachedInteractive",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_local_ip(backend_url: str = "") -> str:
    """Reliably get Laptop A's LAN IP address (not 127.0.0.1)."""
    # 1. Try connecting UDP towards backend host
    if backend_url:
        try:
            parsed = urlparse(backend_url)
            host = parsed.hostname or ""
            port = parsed.port or 80
            if host and not host.startswith("127.") and host != "localhost":
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(1.0)
                s.connect((host, port))
                ip = s.getsockname()[0]
                s.close()
                if ip and not ip.startswith("127."):
                    return ip
        except Exception:
            pass

    # 2. Try standard outbound route to 8.8.8.8
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # 3. Check all host addresses for non-loopback IPv4
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def get_system_info() -> dict:
    """Collect real system hardware and OS specs on Windows."""
    hostname = socket.gethostname()
    computer_name = os.environ.get("COMPUTERNAME") or hostname

    os_name = platform.system()
    os_release = platform.release()
    os_version = platform.version()
    os_full = f"{os_name} {os_release} (Build {os_version})" if os_name else None

    try:
        logged_in_user = os.getlogin()
    except Exception:
        try:
            logged_in_user = getpass.getuser()
        except Exception:
            logged_in_user = os.environ.get("USERNAME")

    mac_address = None
    try:
        node = uuid.getnode()
        mac_address = ':'.join(f"{(node >> i) & 0xff:02x}" for i in range(40, -1, -8))
    except Exception:
        pass

    cpu = platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER")

    ram = None
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            ram_gb = round(stat.ullTotalPhys / (1024**3), 2)
            ram = f"{ram_gb} GB"
    except Exception:
        pass

    manufacturer = None
    model = None
    try:
        import winreg
        reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\SystemInformation")
        manufacturer = winreg.QueryValueEx(reg, "SystemManufacturer")[0]
        model = winreg.QueryValueEx(reg, "SystemProductName")[0]
    except Exception:
        pass

    return {
        "computer_name": computer_name,
        "hostname": hostname,
        "os_name": os_name,
        "os_version": os_full or os_version,
        "logged_in_user": logged_in_user,
        "mac_address": mac_address,
        "cpu": cpu,
        "ram": ram,
        "manufacturer": manufacturer,
        "model": model,
    }


def print_banner(hostname: str, local_ip: str, backend: str, label: str) -> None:
    print(Fore.CYAN + Style.BRIGHT + """
+--------------------------------------------------+
|     AUTH SENTINEL  --  Windows Event Collector   |
|      Real-time Security Event Forwarder          |
|      (Remote Defense & Command Listener Active)  |
+--------------------------------------------------+
""")
    sys_info = get_system_info()
    print(f"  Machine   : {Fore.GREEN}{hostname}{Style.RESET_ALL} ({sys_info.get('manufacturer') or 'PC'})")
    print(f"  LAN IP    : {Fore.GREEN}{local_ip}{Style.RESET_ALL}")
    print(f"  MAC Addr  : {Fore.GREEN}{sys_info.get('mac_address') or 'Unknown'}{Style.RESET_ALL}")
    print(f"  OS / CPU  : {Fore.CYAN}{sys_info.get('os_version') or 'Windows'} | RAM: {sys_info.get('ram') or 'Unknown'}{Style.RESET_ALL}")
    print(f"  Label     : {Fore.YELLOW}{label}{Style.RESET_ALL}")
    print(f"  Backend   : {Fore.GREEN}{backend}{Style.RESET_ALL}")
    print(f"  Watching  : Event IDs {sorted(TARGET_EVENT_IDS)}")
    print(f"  Commands  : Listening for Admin Actions (Shutdown / Lock Screen / Authorize)")
    print()


def parse_event(event, target_computer: str, local_ip: str = "", debug: bool = False) -> Optional[dict]:

    """
    Extract security-event metadata from a pywin32 event record.
    Returns None for uninteresting or system-account events.

    NEVER extracts or transmits passwords.
    """
    try:
        event_id = event.EventID & 0xFFFF
        if event_id not in TARGET_EVENT_IDS:
            return None

        def dropped(reason: str) -> None:
            if debug:
                print(f"[DEBUG] dropped EventID={event_id} reason={reason}")

        # Timestamp
        try:
            t = event.TimeGenerated
            ts = datetime(
                t.year, t.month, t.day, t.hour, t.minute, t.second
            ).astimezone(timezone.utc)
        except Exception:
            ts = datetime.now(timezone.utc)

        strings = event.StringInserts or []
        try:
            raw_username = str(strings[5]).strip()
        except (IndexError, TypeError):
            raw_username = ""
        username    = None
        source_ip   = None
        source_host = None
        logon_type  = None

        if event_id == 4624:
            # Index reference: https://learn.microsoft.com/windows/security/threat-protection/auditing/event-4624
            username    = _str(strings, 5)
            logon_type  = _int(strings, 8)
            source_ip   = _ip(strings, 18)
            source_host = _str(strings, 11)

        elif event_id == 4625:
            # Index reference: https://learn.microsoft.com/windows/security/threat-protection/auditing/event-4625
            username    = _str(strings, 5)
            target_domain = _str(strings, 6)
            sub_status = _str(strings, 9)
            logon_type  = _int(strings, 10)
            source_ip   = _ip(strings, 19)

        # Skip machine and system accounts
        if not username:
            if event_id == 4625 and (target_domain or sub_status):
                username = "UNKNOWN"
            else:
                reason = (
                    f"system account username={raw_username!r}"
                    if raw_username in ("-", "")
                    else "username missing"
                )
                dropped(reason)
                return None
        if username.endswith("$"):
            dropped(f"machine account username={username!r}")
            return None
        if username.upper() in {"SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE"}:
            dropped(f"system account username={username!r}")
            return None
        if username.casefold() in {"window manager", "font driver host"} or username.upper().startswith(
            ("DWM-", "UMFD-")
        ):
            dropped(f"system account username={username!r}")
            return None

        status = "SUCCESS" if event_id == 4624 else "FAILURE"

        # Fallback to Laptop A's LAN IP if source_ip is local or not logged
        if not source_ip or source_ip in ("::1", "127.0.0.1", "-", ""):
            source_ip = local_ip or None

        return {
            "event_id":              event_id,
            "timestamp":             ts.isoformat(),
            "username":              username,
            "source_ip":             source_ip,
            "laptop_ip":             local_ip,
            "source_host":           source_host or target_computer,
            "target_computer":       target_computer,
            "logon_type":            logon_type,
            "logon_type_description": LOGON_TYPES.get(logon_type) if logon_type else None,
            "status":                status,
            "raw_record_id":         event.RecordNumber,
        }
    except Exception as exc:
        logging.debug("parse_event error: %s", exc)
        if debug:
            print(
                f"[DEBUG] dropped EventID={getattr(event, 'EventID', '?')} "
                f"reason=parse error: {exc}"
            )
        return None


def _str(strings: list, idx: int) -> Optional[str]:
    try:
        v = strings[idx].strip()
        return v if v not in ("-", "") else None
    except IndexError:
        return None


def _int(strings: list, idx: int) -> Optional[int]:
    try:
        return int(strings[idx].strip())
    except (IndexError, ValueError, TypeError):
        return None


def _ip(strings: list, idx: int) -> Optional[str]:
    v = _str(strings, idx)
    if v and v not in ("::1", "127.0.0.1", "-", ""):
        return v
    return None


# ── Collector class ───────────────────────────────────────────────────────────

class EventCollector:
    def __init__(self, backend_url: str, label: str, interval: float, debug: bool = False) -> None:
        self.backend_url    = backend_url.rstrip("/")
        self.label          = label
        self.interval       = max(0.05, interval)  # avoid a zero-delay CPU-intensive loop
        self.debug          = debug
        self.hostname       = socket.gethostname()
        self.local_ip       = get_local_ip(self.backend_url)
        self._headers       = {
            "Content-Type":      "application/json",
            "X-Collector-Secret": COLLECTOR_SECRET,
            "X-Source-Label":    self.label,
        }
        self._last_record   = self._get_latest_record()
        print(Fore.CYAN + f"Starting after RecordNumber={self._last_record}")
        self._backend_ok    = False
        self._recent_success = {}
        self._running       = True
        self._command_thread = threading.Thread(target=self._command_worker, daemon=True)
        self._command_thread.start()

    @staticmethod
    def _get_latest_record() -> int:
        """Get the current latest RecordNumber so we only capture FUTURE events."""
        handle = None
        try:
            handle = win32evtlog.OpenEventLog(None, "Security")
            flags = (
                win32evtlog.EVENTLOG_BACKWARDS_READ
                | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            )
            events = win32evtlog.ReadEventLog(handle, flags, 0) or []
            return events[0].RecordNumber if events else 0
        except Exception as exc:
            raise RuntimeError(
                "Cannot read Security log - run as Administrator"
            ) from exc
        finally:
            if handle is not None:
                try:
                    win32evtlog.CloseEventLog(handle)
                except Exception as exc:
                    raise RuntimeError(
                        "Cannot read Security log - run as Administrator"
                    ) from exc

    # ── Backend connectivity ──────────────────────────────────────────────────

    def _health_ok(self) -> bool:
        try:
            r = requests.get(f"{self.backend_url}/api/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _is_duplicate_success(self, parsed: dict) -> bool:
        if parsed.get("event_id") != 4624:
            return False
        key = (
            (parsed.get("username") or "").lower(),
            parsed.get("logon_type"),
            parsed.get("source_ip"),
            parsed.get("source_host"),
        )
        event_time = datetime.fromisoformat(parsed["timestamp"])
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        sent_time = self._recent_success.get(key)
        return (
            sent_time is not None
            and abs((event_time - sent_time).total_seconds()) <= DUP_WINDOW_SECONDS
        )

    def _send_status(self, status: str, message: Optional[str] = None) -> None:
        sys_info = get_system_info()
        payload = {
            "status":        status,
            "hostname":      self.label,       # use label so dashboard shows correct machine name
            "terminal_id":   self.label,
            "ip":            self.local_ip,
            "message":       message,
            "computer_name": sys_info.get("computer_name"),
            "mac_address":   sys_info.get("mac_address"),
            "os_name":       sys_info.get("os_name"),
            "os_version":    sys_info.get("os_version"),
            "logged_in_user":sys_info.get("logged_in_user"),
            "cpu":           sys_info.get("cpu"),
            "ram":           sys_info.get("ram"),
            "manufacturer":  sys_info.get("manufacturer"),
            "model":         sys_info.get("model"),
        }
        try:
            requests.post(
                f"{self.backend_url}/api/collector/status",
                json=payload,
                headers=self._headers,
                timeout=4,
            )
        except Exception:
            pass

    # ── Remote Command Execution (Admin Actions from Dashboard) ───────────────

    def _command_worker(self) -> None:
        """Background thread polling for admin remote commands (shutdown, lock screen, authorize)."""
        while self._running:
            if self._backend_ok:
                try:
                    self._check_for_commands()
                except Exception as exc:
                    logging.debug("Command worker error: %s", exc)
            time.sleep(1.0)

    def _check_for_commands(self) -> None:
        try:
            r = requests.get(
                f"{self.backend_url}/api/collector/commands?terminal_id={self.label}",
                headers=self._headers,
                timeout=4,
            )
            if r.status_code == 200:
                commands = r.json()
                if isinstance(commands, list):
                    for cmd in commands:
                        self._execute_remote_command(cmd)
        except Exception as exc:
            logging.debug("Command check error: %s", exc)

    def _execute_remote_command(self, cmd: dict) -> None:
        cmd_id = cmd.get("id")
        action = (cmd.get("command") or "").lower().strip()
        alert_id = cmd.get("alert_id")
        alert_tag = f" (Alert ALT-{alert_id:04d})" if alert_id else ""

        print()
        print(Fore.MAGENTA + Style.BRIGHT + "==================================================")
        print(Fore.MAGENTA + Style.BRIGHT + f" [ADMIN COMMAND RECEIVED] {action.upper()}{alert_tag}")
        print(Fore.MAGENTA + Style.BRIGHT + "==================================================")

        if action == "lock_screen":
            print(Fore.YELLOW + "  -> Action: Locking Windows workstation immediately ...")
            success = False
            msg = ""
            try:
                if sys.platform == "win32":
                    import ctypes
                    ctypes.windll.user32.LockWorkStation()
                    success = True
                    msg = "Workstation locked successfully via user32.LockWorkStation"
                    print(Fore.GREEN + f"  [EXECUTED] {msg}")
                else:
                    success = True
                    msg = "Non-Windows environment: LockWorkStation simulated"
                    print(Fore.CYAN + f"  [SIMULATION] {msg}")
            except Exception as e:
                msg = f"Failed to lock workstation: {e}"
                print(Fore.RED + f"  [ERROR] {msg}")

            self._ack_command(cmd_id, status="EXECUTED" if success else "FAILED", message=msg)

        elif action == "shutdown":
            print(Fore.RED + Style.BRIGHT + "  -> Action: Remote shutdown command received from Admin!")
            msg = "Windows shutdown sequence initiated with 5-second countdown"
            # Acknowledge to backend BEFORE shutting down so the dashboard receives confirmation!
            self._ack_command(cmd_id, status="EXECUTED", message=msg)
            print(Fore.GREEN + f"  [ACK SENT] Dashboard updated: {msg}")
            print(Fore.RED + "  [EXECUTING] shutdown /s /f /t 5 ...")
            try:
                if sys.platform == "win32":
                    os.system('shutdown /s /f /t 5 /c "Security Alert: Remote system shutdown initiated by AuthSentinel Admin"')
                else:
                    print(Fore.CYAN + "  [SIMULATION] Non-Windows environment: shutdown simulated.")
            except Exception as e:
                print(Fore.RED + f"  [ERROR] Shutdown execution error: {e}")

        elif action == "authorize":
            print(Fore.GREEN + "  -> Notice: Administrator authorized activity — marked benign (No problem).")
            self._ack_command(cmd_id, status="EXECUTED", message="Authorization acknowledged by Laptop A")

        else:
            print(Fore.YELLOW + f"  [WARN] Unknown action: {action}")
            self._ack_command(cmd_id, status="FAILED", message=f"Unknown action: {action}")

    def _ack_command(self, cmd_id: int, status: str, message: str) -> None:
        try:
            requests.post(
                f"{self.backend_url}/api/collector/commands/{cmd_id}/ack",
                json={"status": status, "message": message},
                headers=self._headers,
                timeout=5,
            )
        except Exception as exc:
            logging.debug("Ack command exception: %s", exc)


    def _post_event(self, payload: dict) -> str:
        try:
            r = requests.post(
                f"{self.backend_url}/api/events",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            if r.status_code == 200:
                return "ok"
            if r.status_code == 403:
                print(
                    Fore.RED
                    + "Invalid collector secret: set the same AS_COLLECTOR_SECRET "
                    + "on both laptops"
                )
                return "fatal"
            if 400 <= r.status_code < 500:
                print(
                    Fore.RED
                    + f"  [HTTP ERROR] status={r.status_code} "
                    + f"response={r.text[:200]}"
                )
                return "skip"
            if r.status_code >= 500:
                print(
                    Fore.RED
                    + f"  [HTTP ERROR] status={r.status_code} "
                    + f"response={r.text[:200]}"
                )
                return "retry"
            print(
                Fore.RED
                + f"  [HTTP ERROR] status={r.status_code} "
                + f"response={r.text[:200]}"
            )
            return "retry"
        except (requests.ConnectionError, requests.Timeout):
            return "retry"
        except Exception as exc:
            logging.debug("post_event error: %s", exc)
            return "retry"

    # ── Wait for backend ──────────────────────────────────────────────────────

    def _wait_for_backend(self) -> None:
        attempt = 0
        while not self._health_ok():
            attempt += 1
            print(
                Fore.YELLOW
                + f"  [{attempt}] Backend unavailable -- Retrying in 5s ... ({self.backend_url})"
            )
            time.sleep(5)
        print(Fore.GREEN + f"  [OK] Backend connected: {self.backend_url}")
        self._backend_ok = True
        self._send_status("CONNECTED", f"Collector on {self.label} ({self.local_ip}) started")

    # ── Poll Security Event Log ───────────────────────────────────────────────

    def poll(self) -> None:
        prune_before = datetime.now(timezone.utc).timestamp() - 60
        self._recent_success = {
            key: sent_time
            for key, sent_time in self._recent_success.items()
            if sent_time.timestamp() >= prune_before
        }
        handle = None
        try:
            handle = win32evtlog.OpenEventLog(None, "Security")
            flags  = (
                win32evtlog.EVENTLOG_BACKWARDS_READ
                | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            )
            first_batch = win32evtlog.ReadEventLog(handle, flags, 0) or []
            newest_record = 0
            for event in first_batch:
                try:
                    newest_record = max(newest_record, event.RecordNumber)
                except Exception:
                    logging.exception(
                        "Skipping malformed Security event while checking log cursor"
                    )

            if (
                self._last_record
                and newest_record
                and newest_record < self._last_record
            ):
                print(Fore.YELLOW + "Security log was cleared; resetting cursor")
                self._last_record = 0
                self._recent_success.clear()

            if self._last_record == 0:
                for event in first_batch:
                    try:
                        record_number = event.RecordNumber
                        if self.debug:
                            print(
                                f"[DEBUG] RecordNumber={record_number} "
                                f"EventID={event.EventID & 0xFFFF} "
                                f"StringInserts={list(event.StringInserts or [])[:6]!r}"
                            )
                    except Exception:
                        logging.exception(
                            "Skipping malformed Security event while establishing cursor"
                        )
                if newest_record:
                    self._last_record = newest_record
                    print(
                        Fore.CYAN
                        + f"Starting after RecordNumber={self._last_record}"
                    )
                return

            raw_events = []
            reached_last_record = False
            batches = [first_batch]
            while True:
                batch = batches.pop() if batches else (
                    win32evtlog.ReadEventLog(handle, flags, 0) or []
                )
                if not batch:
                    break
                for event in batch:
                    try:
                        record_number = event.RecordNumber
                    except Exception:
                        logging.exception(
                            "Skipping malformed Security event while reading"
                        )
                        continue
                    if self.debug:
                        try:
                            print(
                                f"[DEBUG] RecordNumber={record_number} "
                                f"EventID={event.EventID & 0xFFFF} "
                                f"StringInserts={list(event.StringInserts or [])[:6]!r}"
                            )
                        except Exception:
                            logging.exception(
                                "Could not print debug fields for Security event "
                                "RecordNumber=%s",
                                record_number,
                            )
                    if record_number <= self._last_record:
                        reached_last_record = True
                        break
                    raw_events.append(event)
                if reached_last_record:
                    break
        except Exception as exc:
            print(Fore.RED + f"  [ERROR] Cannot read Security log: {exc}")
            print(Fore.YELLOW + "  -> Make sure you are running as Administrator")
            return
        finally:
            if handle is not None:
                try:
                    win32evtlog.CloseEventLog(handle)
                except Exception as exc:
                    logging.debug("close_event_log error: %s", exc)

        # Process newly-read records oldest first, advancing over unrelated Security events too.
        new_events = sorted(
            raw_events,
            key=lambda e: e.RecordNumber,
        )

        for ev in new_events:
            record_number = None
            try:
                record_number = ev.RecordNumber
                if (ev.EventID & 0xFFFF) in TARGET_EVENT_IDS:
                    parsed = parse_event(
                        ev,
                        target_computer=self.label,
                        local_ip=self.local_ip,
                        debug=self.debug,
                    )
                    if parsed:
                        # Event ID 4624 with logon type 7 is a workstation unlock,
                        # not a new interactive login. Do not forward it as a second login.
                        if parsed["event_id"] == 4624 and parsed.get("logon_type") == 7:
                            print(Style.DIM + "  [SKIP] Windows unlock event (logon_type=7) ignored")
                            self._last_record = record_number
                            continue

                        if self._is_duplicate_success(parsed):
                            print(
                                Style.DIM
                                + "  [DEDUP] duplicate 4624 token event ignored"
                            )
                            self._last_record = record_number
                            continue

                        self._print_event(parsed)

                        result = self._post_event(parsed)
                        if result == "ok":
                            if parsed["event_id"] == 4624:
                                key = (
                                    (parsed.get("username") or "").lower(),
                                    parsed.get("logon_type"),
                                    parsed.get("source_ip"),
                                    parsed.get("source_host"),
                                )
                                event_time = datetime.fromisoformat(parsed["timestamp"])
                                if event_time.tzinfo is None:
                                    event_time = event_time.replace(
                                        tzinfo=timezone.utc
                                    )
                                self._recent_success[key] = event_time
                            print(
                                Fore.GREEN
                                + f"  [SENT] event_id={parsed['event_id']}"
                                + f"  user={parsed['username']}"
                                + f"  src={parsed.get('source_ip') or parsed.get('source_host') or '-'}"
                                + f"  --> backend accepted"
                            )
                        elif result == "fatal":
                            raise SystemExit(1)
                        elif result == "retry":
                            print(
                                Fore.RED
                                + "  [FAIL] Event POST failed; see HTTP diagnostics or check connectivity"
                            )
                            self._backend_ok = False
                            break
                        elif result == "skip":
                            print(
                                Fore.YELLOW
                                + f"  [SKIP] event_id={parsed['event_id']} rejected by backend; "
                                + "moving to the next event"
                            )

                self._last_record = record_number
            except Exception:
                logging.exception(
                    "Failed to process Security event RecordNumber=%s",
                    record_number,
                )
                if record_number is not None:
                    self._last_record = record_number

    def _print_event(self, ev: dict) -> None:
        eid    = ev["event_id"]
        user   = ev.get("username", "?")
        src    = ev.get("source_ip") or ev.get("source_host") or "local"
        ltype  = ev.get("logon_type_description") or "-"
        status = ev["status"]

        color  = Fore.GREEN if status == "SUCCESS" else Fore.RED
        icon   = "[SUCCESS]" if status == "SUCCESS" else "[FAILURE]"

        print()
        print(color + f"  {icon}  Event {eid}")
        print(Fore.WHITE + f"  [PARSED]    user={user}  source={src}  logon_type={ltype}")
        print(Fore.YELLOW + f"  [DETECTION] Forwarding to detection engine ...")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        print_banner(self.hostname, self.local_ip, self.backend_url, self.label)
        print(f"Events will appear on the dashboard as source_host={self.label}")
        print(f"Polling interval: {self.interval * 1000:.0f} ms (near-real-time; network/backend/UI latency still applies)")
        print(
            "Failed logons: forwarding 4625 events; wrong PIN attempts on Windows Hello may not be logged by Windows"
        )
        self._wait_for_backend()

        print(Fore.GREEN + "[RUNNING] Collector active -- waiting for Windows auth events ...\n")

        try:
            last_heartbeat = time.monotonic()
            while True:
                if not self._backend_ok:
                    print(Fore.YELLOW + "\n[RECONNECT] Backend unavailable -- retrying ...")
                    if self._health_ok():
                        self._backend_ok = True
                        self._send_status("CONNECTED", f"{self.label} reconnected")
                        print(Fore.GREEN + "[OK] Backend reconnected\n")
                now = time.monotonic()
                if now - last_heartbeat >= 30:
                    self._send_status(
                        "CONNECTED",
                        f"Collector on {self.label} ({self.local_ip}) heartbeat",
                    )
                    last_heartbeat = now
                self.poll()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n[STOPPING] Shutting down collector ...")
        finally:
            self._send_status("DISCONNECTED", f"Collector on {self.label} stopped")
            print(Fore.CYAN + "[STOPPED]")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if sys.platform != "win32":
        print("ERROR: This collector requires Windows (win32evtlog).")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="AuthSentinel Windows Event Collector",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--backend",
        default=os.environ.get("AS_COLLECTOR_BACKEND_URL", "http://127.0.0.1:8000"),
        help="AuthSentinel backend URL  (Laptop A should set this to http://LAPTOP-B-IP:8000)",
    )
    parser.add_argument(
        "--label",
        default=socket.gethostname(),
        help="Source label shown on the dashboard (e.g. LAPTOP-A)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("AS_COLLECTOR_POLL_INTERVAL", "0.1")),
        help="Poll interval in seconds; 0.1 means check for new events every 100 ms",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print RecordNumber, EventID, and the first six StringInserts for each Security event read",
    )
    args = parser.parse_args()

    try:
        collector = EventCollector(
            backend_url=args.backend,
            label=args.label,
            interval=args.interval,
            debug=args.debug,
        )
    except RuntimeError as exc:
        print(Fore.RED + str(exc))
        sys.exit(1)
    collector.run()


if __name__ == "__main__":
    main()
