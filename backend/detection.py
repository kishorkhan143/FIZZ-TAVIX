"""
AuthSentinel — Detection Engine
================================
Correlates raw auth events into alerts.

Rules implemented:
  1. REPEATED_FAILURE   — N failures within T seconds for same user+source
  2. SUCCESS_AFTER_FAILURES — success after ≥ threshold failures
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Optional

from config import settings

logger = logging.getLogger("authsentinel.detection")


# ── In-memory sliding window per (username, source_ip) ──────────────────────
# Each entry: dict  {"timestamp": datetime, "event_id": int, "status": str}
_windows: dict[str, deque] = {}
_success_alerted: set[str] = set()


def _key(username: str, source_ip: str) -> str:
    return f"{username}|{source_ip}"


def _prune(dq: deque, cutoff: datetime) -> None:
    """Remove entries older than the cutoff datetime."""
    while dq and dq[0]["timestamp"] < cutoff:
        dq.popleft()


def evaluate(
    event_id: int,
    username: str,
    source_ip: str,
    timestamp: datetime,
    status: str,
) -> Optional[dict]:
    """
    Evaluate a single auth event.

    Returns an alert dict if a rule fires, otherwise None.
    Never persists—caller handles DB writes.
    """
    if not username or username.strip() in ("", "-", "SYSTEM"):
        return None

    key = _key(username, source_ip)
    if key not in _windows:
        _windows[key] = deque()

    dq = _windows[key]
    cutoff = timestamp - timedelta(seconds=settings.brute_force_window_seconds)
    _prune(dq, cutoff)

    dq.append({"timestamp": timestamp, "event_id": event_id, "status": status})

    # ── Rule 1: Repeated failures ─────────────────────────────────────────
    if status == "FAILURE":
        _success_alerted.discard(key)
        failures_in_window = sum(1 for e in dq if e["status"] == "FAILURE")

        if failures_in_window == settings.brute_force_threshold:
            # Fire exactly when crossing the threshold (not every subsequent event)
            logger.warning(
                "[DETECTION] REPEATED_FAILURE | user=%s src=%s count=%d",
                username,
                source_ip,
                failures_in_window,
            )
            return {
                "alert_type": "REPEATED_FAILURE",
                "username": username,
                "source_ip": source_ip,
                "risk_score": 85.0,
                "risk_level": "HIGH",
                "failure_count": failures_in_window,
                "time_window_seconds": settings.brute_force_window_seconds,
                "reason": (
                    f"Multiple failed authentication events were observed for the same "
                    f"account/source within the configured detection window. "
                    f"{failures_in_window} failures detected in "
                    f"{settings.brute_force_window_seconds} seconds."
                ),
            }

    # ── Rule 2: Success after multiple failures ───────────────────────────
    if status == "SUCCESS":
        failures_before = sum(1 for e in dq if e["status"] == "FAILURE")

        if (
            failures_before >= settings.success_after_failures_threshold
            and key not in _success_alerted
        ):
            _success_alerted.add(key)
            logger.warning(
                "[DETECTION] SUCCESS_AFTER_FAILURES | user=%s src=%s prior_failures=%d",
                username,
                source_ip,
                failures_before,
            )
            return {
                "alert_type": "SUCCESS_AFTER_FAILURES",
                "username": username,
                "source_ip": source_ip,
                "risk_score": 90.0,
                "risk_level": "HIGH",
                "failure_count": failures_before,
                "time_window_seconds": settings.brute_force_window_seconds,
                "reason": (
                    f"A successful authentication occurred after {failures_before} "
                    f"recent authentication failures. This is a suspicious "
                    f"authentication pattern requiring investigation."
                ),
            }

        # ── Rule 3: Unusual login outside lab hours ───────────────────────────
        if not is_within_lab_hours(timestamp):
            start_str = _lab_hours.get("start_time", "09:00")
            end_str = _lab_hours.get("end_time", "18:00")
            logger.warning(
                "[DETECTION] UNUSUAL_LOGIN | user=%s src=%s outside lab hours (%s - %s)",
                username,
                source_ip,
                start_str,
                end_str,
            )
            return {
                "alert_type": "UNUSUAL_LOGIN",
                "username": username,
                "source_ip": source_ip,
                "risk_score": 80.0,
                "risk_level": "HIGH",
                "failure_count": 0,
                "time_window_seconds": 0,
                "reason": (
                    f"Unusual Login Alert: Account '{username}' opened outside "
                    f"authorized laboratory operating hours ({start_str} - {end_str})."
                ),
            }

    return None


# ── Lab Operating Hours Configuration ───────────────────────────────────────
import json
import os

LAB_HOURS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_hours.json")

_lab_hours: dict[str, str] = {
    "start_time": "09:00",
    "end_time": "18:00",
}


def load_lab_hours() -> None:
    global _lab_hours
    try:
        if os.path.exists(LAB_HOURS_FILE):
            with open(LAB_HOURS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "start_time" in data and "end_time" in data:
                    _lab_hours["start_time"] = data["start_time"]
                    _lab_hours["end_time"] = data["end_time"]
    except Exception as e:
        logger.warning("Failed to load lab_hours.json: %s", e)


def save_lab_hours() -> None:
    try:
        with open(LAB_HOURS_FILE, "w", encoding="utf-8") as f:
            json.dump(_lab_hours, f, indent=2)
    except Exception as e:
        logger.warning("Failed to save lab_hours.json: %s", e)


load_lab_hours()


def is_within_lab_hours(dt: datetime, start_time: Optional[str] = None, end_time: Optional[str] = None) -> bool:
    if start_time is None:
        start_time = _lab_hours.get("start_time", "09:00")
    if end_time is None:
        end_time = _lab_hours.get("end_time", "18:00")

    try:
        sh, sm = map(int, start_time.split(":"))
        eh, em = map(int, end_time.split(":"))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        curr_min = dt.hour * 60 + dt.minute

        if start_min <= end_min:
            return start_min <= curr_min < end_min
        else:
            return curr_min >= start_min or curr_min < end_min
    except Exception:
        return True


def set_lab_hours(start_time: str, end_time: str) -> dict:
    _lab_hours["start_time"] = start_time
    _lab_hours["end_time"] = end_time
    save_lab_hours()
    return get_lab_hours()


def get_lab_hours() -> dict:
    now = datetime.now()
    is_open = is_within_lab_hours(now)
    return {
        "start_time": _lab_hours["start_time"],
        "end_time": _lab_hours["end_time"],
        "is_open": is_open,
        "status": "USUAL" if is_open else "UNUSUAL_ALERT",
    }


def reset_window(username: str, source_ip: str) -> None:
    """Clear the sliding window for a user/source pair (e.g. after alert acknowledged)."""
    key = _key(username, source_ip)
    _windows.pop(key, None)
    _success_alerted.discard(key)
