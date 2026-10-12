"""
AuthSentinel — Anomaly Detection Engine
========================================
Detects statistical anomalies beyond rule-based thresholds:
  1. Failure Velocity — Accelerating failure rate
  2. Success Anomaly — Unusual rapid success after consistent failures
  3. Burst Detection — Cluster of events in short time window
"""

import logging
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional
from statistics import mean, stdev

logger = logging.getLogger("authsentinel.anomaly")

# --- In-memory statistics per (username, source_ip) --------------------------
_failure_history = defaultdict(lambda: deque(maxlen=20))
_success_history = defaultdict(lambda: deque(maxlen=20))
_event_intervals = defaultdict(lambda: deque(maxlen=15))


def _key(username: str, source_ip: str) -> str:
    return f"{username}|{source_ip}"


def evaluate_anomalies(
    username: str,
    source_ip: str,
    timestamp: datetime,
    status: str,
) -> Optional[dict]:
    """Evaluate event for statistical anomalies."""
    if not username or username.strip() in ("", "-", "SYSTEM"):
        return None

    key = _key(username, source_ip)

    # Rule 1: Failure Velocity
    if status == "FAILURE":
        failure_deque = _failure_history[key]
        failure_deque.append(timestamp)

        if len(failure_deque) >= 5:
            intervals = []
            for i in range(1, len(failure_deque)):
                delta = (failure_deque[i] - failure_deque[i - 1]).total_seconds()
                intervals.append(delta)

            if len(intervals) >= 3:
                recent_intervals = intervals[-3:]
                avg_recent = mean(recent_intervals)
                earlier_intervals = intervals[:-3]
                avg_earlier = mean(earlier_intervals) if earlier_intervals else avg_recent * 2

                acceleration_ratio = avg_earlier / avg_recent if avg_recent > 0 else 1
                
                if acceleration_ratio > 2.5:
                    logger.warning(
                        "[ANOMALY] FAILURE_VELOCITY | user=%s src=%s ratio=%.2f",
                        username,
                        source_ip,
                        acceleration_ratio,
                    )
                    return {
                        "alert_type": "FAILURE_VELOCITY",
                        "username": username,
                        "source_ip": source_ip,
                        "risk_score": 75.0,
                        "risk_level": "HIGH",
                        "failure_count": len(failure_deque),
                        "time_window_seconds": int(
                            (failure_deque[-1] - failure_deque[0]).total_seconds()
                        ),
                        "reason": (
                            f"Anomaly detected: Authentication failures are accelerating. "
                            f"Recent failures {acceleration_ratio:.1f}x faster than historical baseline. "
                            f"This pattern suggests automated attack tools."
                        ),
                    }

    # Rule 2: Success Anomaly
    if status == "SUCCESS":
        failure_deque = _failure_history[key]
        success_deque = _success_history[key]
        success_deque.append(timestamp)

        if len(failure_deque) >= 3:
            if len(failure_deque) >= 2:
                failure_intervals = [
                    (failure_deque[i] - failure_deque[i - 1]).total_seconds()
                    for i in range(1, len(failure_deque))
                ]
                avg_failure_interval = mean(failure_intervals)
                time_to_success = (timestamp - failure_deque[-1]).total_seconds()
                
                if time_to_success < avg_failure_interval * 0.3:
                    logger.warning(
                        "[ANOMALY] SUCCESS_ANOMALY | user=%s src=%s",
                        username,
                        source_ip,
                    )
                    return {
                        "alert_type": "SUCCESS_ANOMALY",
                        "username": username,
                        "source_ip": source_ip,
                        "risk_score": 80.0,
                        "risk_level": "HIGH",
                        "failure_count": len(failure_deque),
                        "time_window_seconds": int(time_to_success),
                        "reason": (
                            f"Anomaly detected: Rapid success after failed attempts. "
                            f"Suggests possible credential compromise."
                        ),
                    }

    # Rule 3: Burst Detection
    _event_intervals[key].append((timestamp, status))
    events_in_window = _event_intervals[key]
    
    if len(events_in_window) >= 8:
        time_span = (events_in_window[-1][0] - events_in_window[0][0]).total_seconds()
        
        if time_span < 60 and time_span > 0:
            burst_failures = sum(1 for _, s in events_in_window if s == "FAILURE")
            
            logger.warning(
                "[ANOMALY] BURST_DETECTED | user=%s src=%s events=%d timespan=%.0f",
                username,
                source_ip,
                len(events_in_window),
                time_span,
            )
            return {
                "alert_type": "BURST_DETECTED",
                "username": username,
                "source_ip": source_ip,
                "risk_score": 70.0,
                "risk_level": "HIGH",
                "failure_count": burst_failures,
                "time_window_seconds": int(time_span),
                "reason": (
                    f"Anomaly detected: High-velocity event burst. "
                    f"{len(events_in_window)} events in {time_span:.0f}s. "
                    f"Indicative of automated attack tools."
                ),
            }

    return None


def get_user_baseline(username: str, source_ip: str) -> dict:
    """Return baseline statistics for a user."""
    key = _key(username, source_ip)
    
    failure_deque = _failure_history.get(key, deque())
    success_deque = _success_history.get(key, deque())
    
    if len(failure_deque) >= 2:
        intervals = [
            (failure_deque[i] - failure_deque[i - 1]).total_seconds()
            for i in range(1, len(failure_deque))
        ]
        avg_interval = mean(intervals)
        std_interval = stdev(intervals) if len(intervals) > 1 else 0
    else:
        avg_interval = 0
        std_interval = 0
    
    return {
        "username": username,
        "source_ip": source_ip,
        "total_failures": len(failure_deque),
        "total_successes": len(success_deque),
        "avg_failure_interval_seconds": avg_interval,
        "failure_interval_std_dev": std_interval,
        "last_failure": failure_deque[-1].isoformat() if failure_deque else None,
        "last_success": success_deque[-1].isoformat() if success_deque else None,
    }


def reset_user(username: str, source_ip: str) -> None:
    """Clear history for a user."""
    key = _key(username, source_ip)
    _failure_history.pop(key, None)
    _success_history.pop(key, None)
    _event_intervals.pop(key, None)
    logger.info("[ANOMALY] User history cleared: user=%s src=%s", username, source_ip)
