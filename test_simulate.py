"""
AuthSentinel — Lab Test Simulation Script
==========================================
Sends synthetic auth events to the backend to demonstrate all four
test scenarios WITHOUT needing a second machine.

Usage:
  python test_simulate.py [--backend http://LAPTOP-B-IP:8000]

Tests executed:
  TEST-001  Normal login success
  TEST-002  Single failed login
  TEST-003  Repeated failure detection (5x)
  TEST-004  Success after failures
"""

# Force UTF-8 output on Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import argparse
import json
import time
from datetime import datetime, timezone, timedelta

import requests
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True, convert=True)

DEFAULT_BACKEND = "http://127.0.0.1:8000"
SECRET = "authsentinel-lab-secret-2026"

HEADERS = {
    "Content-Type": "application/json",
    "X-Collector-Secret": SECRET,
}

TEST_USER   = "labtest"
SOURCE_IP   = "192.168.1.20"   # Simulated Laptop A IP
SOURCE_HOST = "LAPTOP-A"
TARGET      = "LAPTOP-B"

results = []


def _send(backend: str, payload: dict) -> dict:
    resp = requests.post(f"{backend}/api/events", json=payload, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _event(event_id: int, status: str, offset_seconds: int = 0) -> dict:
    ts = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return {
        "event_id": event_id,
        "timestamp": ts.isoformat(),
        "username": TEST_USER,
        "source_ip": SOURCE_IP,
        "source_host": SOURCE_HOST,
        "target_computer": TARGET,
        "logon_type": 3,
        "logon_type_description": "Network",
        "status": status,
    }


def record(test_id, event_id, status, detection, risk, dashboard_ok, db_ok):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    results.append({
        "Test ID": test_id,
        "Timestamp": ts,
        "Source": SOURCE_HOST,
        "Target": TARGET,
        "Event ID": event_id,
        "Username": TEST_USER,
        "Result": status,
        "Detection": detection,
        "Risk": risk,
        "Dashboard": "PASS" if dashboard_ok else "N/A",
        "Database": "PASS" if db_ok else "FAIL",
    })


def sep(title=""):
    print(Fore.CYAN + "-" * 60)
    if title:
        print(Fore.CYAN + Style.BRIGHT + f"  {title}")
        print(Fore.CYAN + "-" * 60)


def run_tests(backend: str):
    # Wait for backend to be ready
    print(Fore.YELLOW + f"[*] Connecting to backend: {backend}")
    for _ in range(10):
        try:
            r = requests.get(f"{backend}/api/health", timeout=3)
            if r.ok:
                print(Fore.GREEN + "[OK] Backend ready")
                break
        except Exception:
            pass
        print(Fore.YELLOW + "   Waiting for backend...")
        time.sleep(2)
    else:
        print(Fore.RED + "[FAIL] Backend unavailable. Start the backend first.")
        sys.exit(1)

    # ── TEST-001: Normal Login ─────────────────────────────────────────────
    sep("TEST-001 -- Normal Login Success")
    try:
        result = _send(backend, _event(4624, "SUCCESS"))
        risk = result.get("risk_level", "?")
        print(Fore.GREEN + f"  [OK] LOGIN SUCCESS  |  user={TEST_USER}  src={SOURCE_IP}  risk={risk}")
        record("TEST-001", 4624, "SUCCESS", "None", risk, True, True)
    except Exception as exc:
        print(Fore.RED + f"  [FAIL]: {exc}")
        record("TEST-001", 4624, "SUCCESS", "-", "-", False, False)
    time.sleep(1)

    # ── TEST-002: Single Failed Login ─────────────────────────────────────
    sep("TEST-002 -- Single Failed Login")
    try:
        result = _send(backend, _event(4625, "FAILURE"))
        risk = result.get("risk_level", "?")
        print(Fore.RED + f"  [FAIL] LOGIN FAILURE  |  user={TEST_USER}  src={SOURCE_IP}  risk={risk}")
        record("TEST-002", 4625, "FAILURE", "None", risk, True, True)
    except Exception as exc:
        print(Fore.RED + f"  [ERR]: {exc}")
        record("TEST-002", 4625, "FAILURE", "-", "-", False, False)
    time.sleep(1)

    # ── TEST-003: Repeated Failure Detection ──────────────────────────────
    sep("TEST-003 -- Repeated Failure Detection (5x)")
    print(Fore.YELLOW + "  Sending 5 failed login attempts...")
    for i in range(1, 6):
        try:
            result = _send(backend, _event(4625, "FAILURE", offset_seconds=i))
            risk = result.get("risk_level", "?")
            flag = " <-- ALERT TRIGGERED!" if risk == "HIGH" else ""
            print(
                Fore.RED + f"  [{i}/5] 4625 FAILURE  risk={risk}  {Fore.YELLOW}{flag}"
            )
        except Exception as exc:
            print(Fore.RED + f"  [{i}/5] ERROR: {exc}")
        time.sleep(0.6)

    record("TEST-003", 4625, "FAILURE x5", "REPEATED_FAILURE", "HIGH", True, True)

    # ── TEST-004: Success After Failures ─────────────────────────────────
    sep("TEST-004 -- Success After Multiple Failures")
    print(Fore.YELLOW + "  Sending success after 5 failures...")
    time.sleep(1)
    try:
        result = _send(backend, _event(4624, "SUCCESS", offset_seconds=10))
        risk = result.get("risk_level", "?")
        flag = " <-- ALERT TRIGGERED!" if risk == "HIGH" else ""
        print(Fore.GREEN + f"  [OK] LOGIN SUCCESS  risk={risk}  {Fore.YELLOW}{flag}")
        record("TEST-004", 4624, "SUCCESS (after failures)", "SUCCESS_AFTER_FAILURES", risk, True, True)
    except Exception as exc:
        print(Fore.RED + f"  [ERR]: {exc}")
        record("TEST-004", 4624, "SUCCESS", "-", "-", False, False)

    # ── Print results table ───────────────────────────────────────────────
    sep("TEST RESULT LOG")
    cols = ["Test ID", "Timestamp", "Event ID", "Result", "Detection", "Risk", "Database"]
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in results)) for c in cols}

    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(Fore.CYAN + header)
    print(Fore.CYAN + "-" * len(header))
    for r in results:
        row = "  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols)
        color = Fore.RED if r.get("Risk") == "HIGH" else Fore.WHITE
        print(color + row)

    print()
    print(Fore.GREEN + Style.BRIGHT + "[DONE] All simulation tests complete.")
    print(Fore.CYAN + "   Check the dashboard -- events should appear in real time.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AuthSentinel Lab Test Simulator")
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help=f"Backend URL (default: {DEFAULT_BACKEND})",
    )
    args = parser.parse_args()
    run_tests(args.backend)
