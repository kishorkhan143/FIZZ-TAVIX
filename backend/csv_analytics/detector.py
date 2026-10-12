"""
Security Alert Detection Engine
===============================
Implements 10 intelligent security detection rules with correlated grouping
to prevent alert fatigue:
  1. Multiple Failed Logins
  2. Brute Force Pattern
  3. Unusual Login Frequency
  4. Multiple Countries (Impossible Travel / Geo Anomaly)
  5. IP Anomaly (Password Spraying / Multi-Account Activity)
  6. High Error Rate
  7. Event Volume Spike
  8. Suspicious Event Types & Security Signals
  9. High Severity Records
  10. Repeated Suspicious Behavior (Compound escalation)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict


class SecurityDetector:
    """Evaluates normalized event records and produces structured, deduplicated security alerts."""

    @classmethod
    def detect_alerts(
        cls,
        import_id: str,
        records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Analyzes normalized event records and generates correlated alerts.

        Args:
            import_id: Unique ID of the CSV import
            records: List of normalized event dicts (sorted by timestamp)

        Returns:
            List of structured alert dicts
        """
        if not records:
            return []

        # Sort records chronologically
        sorted_records = sorted(records, key=lambda r: r["timestamp"])

        # Groupings for multi-dimensional analysis
        user_events = defaultdict(list)
        ip_events = defaultdict(list)
        time_windows = defaultdict(list)  # 2-minute bucket keys

        for rec in sorted_records:
            u = rec.get("user")
            ip = rec.get("ip")
            if u:
                user_events[u].append(rec)
            if ip and ip != "0.0.0.0":
                ip_events[ip].append(rec)

            # 2-minute bucket
            ts = rec["timestamp"]
            bucket = ts.strftime("%Y-%m-%d %H:") + f"{(ts.minute // 2) * 2:02d}"
            time_windows[bucket].append(rec)

        # Baseline metrics
        total_records_count = len(sorted_records)
        unique_users_count = len(user_events) or 1
        avg_events_per_user = total_records_count / unique_users_count

        alerts_map: Dict[str, Dict[str, Any]] = {}
        alert_counter = 1

        def add_or_merge_alert(
            key: str,
            alert_type: str,
            severity: str,
            risk_score: float,
            user: Optional[str],
            ip: Optional[str],
            country: Optional[str],
            message: str,
            reasons: List[str],
            related_recs: List[Dict[str, Any]],
        ):
            nonlocal alert_counter
            if not related_recs:
                return

            timestamps = [r["timestamp"] for r in related_recs]
            first_seen = min(timestamps)
            last_seen = max(timestamps)
            window_sec = max(0, int((last_seen - first_seen).total_seconds()))
            failed_count = sum(1 for r in related_recs if r.get("status") == "FAILURE")
            event_count = len(related_recs)
            row_numbers = [r["row_number"] for r in related_recs]

            if key in alerts_map:
                existing = alerts_map[key]
                # Escalate severity if higher
                sev_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
                if sev_order.get(severity, 1) > sev_order.get(existing["severity"], 1):
                    existing["severity"] = severity
                existing["risk_score"] = min(100.0, max(existing["risk_score"], risk_score) + 5.0)
                # Combine reasons
                for r in reasons:
                    if r not in existing["reasons"]:
                        existing["reasons"].append(r)
                # Combine rows
                combined_rows = sorted(list(set(existing["related_events"] + row_numbers)))
                existing["related_events"] = combined_rows
                existing["event_count"] = len(combined_rows)
                existing["failed_count"] = max(existing["failed_count"], failed_count)
                existing["first_seen"] = min(existing["first_seen"], first_seen)
                existing["last_seen"] = max(existing["last_seen"], last_seen)
                existing["time_window_seconds"] = max(0, int((existing["last_seen"] - existing["first_seen"]).total_seconds()))
            else:
                alert_id = f"ALERT-{alert_counter:03d}"
                alert_counter += 1
                alerts_map[key] = {
                    "id": alert_id,
                    "import_id": import_id,
                    "alert_type": alert_type,
                    "severity": severity,
                    "risk_score": min(100.0, float(risk_score)),
                    "user": user,
                    "ip": ip,
                    "country": country,
                    "message": message,
                    "first_seen": first_seen,
                    "last_seen": last_seen,
                    "event_count": event_count,
                    "failed_count": failed_count,
                    "time_window_seconds": window_sec,
                    "status": "OPEN",
                    "reasons": reasons,
                    "related_events": sorted(list(set(row_numbers))),
                    "created_at": datetime.now(timezone.utc),
                }

        # -------------------------------------------------------------
        # RULE 1: Multiple Failed Logins (by User and by IP)
        # -------------------------------------------------------------
        for user, u_recs in user_events.items():
            failures = [r for r in u_recs if r.get("status") == "FAILURE"]
            if len(failures) >= 3:
                # Check timeframe of failures
                dt = (failures[-1]["timestamp"] - failures[0]["timestamp"]).total_seconds()
                if dt <= 1800 or len(failures) >= 4:  # within 30 mins or >= 4 failures
                    window_desc = f"{int(dt // 60)} minutes" if dt >= 60 else f"{int(dt)} seconds"
                    sev = "CRITICAL" if len(failures) >= 8 else ("HIGH" if len(failures) >= 4 else "MEDIUM")
                    score = 90.0 if len(failures) >= 8 else (78.0 if len(failures) >= 4 else 55.0)
                    add_or_merge_alert(
                        key=f"RULE1_USER_{user}",
                        alert_type="MULTIPLE_FAILURES",
                        severity=sev,
                        risk_score=score,
                        user=user,
                        ip=failures[0].get("ip"),
                        country=failures[0].get("country"),
                        message=f"Multiple failed login attempts detected for user '{user}'",
                        reasons=[
                            f"{len(failures)} failed login attempts detected",
                            f"Time window: {window_desc}" if dt > 0 else "Instantaneous repeated failures",
                        ],
                        related_recs=failures,
                    )

        # -------------------------------------------------------------
        # RULE 2: Brute Force Pattern (Rapid repeated failures from same IP)
        # -------------------------------------------------------------
        for ip, ip_recs in ip_events.items():
            failures = [r for r in ip_recs if r.get("status") == "FAILURE"]
            if len(failures) >= 4:
                window_sec = (failures[-1]["timestamp"] - failures[0]["timestamp"]).total_seconds()
                velocity = (len(failures) / max(1, window_sec)) * 60.0  # failures per minute
                targeted_users = list({r.get("user") for r in failures if r.get("user")})
                if velocity >= 2.0 or len(failures) >= 6:
                    add_or_merge_alert(
                        key=f"RULE2_IP_{ip}",
                        alert_type="BRUTE_FORCE",
                        severity="CRITICAL" if len(failures) >= 10 else "HIGH",
                        risk_score=90.0 if len(failures) >= 10 else 82.0,
                        user=targeted_users[0] if len(targeted_users) == 1 else "multiple_users",
                        ip=ip,
                        country=failures[0].get("country"),
                        message=f"Brute force authentication attack pattern detected from IP {ip}",
                        reasons=[
                            f"{len(failures)} repeated login failures from IP {ip}",
                            f"Failure velocity: {velocity:.1f} attempts per minute",
                            f"Targeted accounts: {', '.join(targeted_users[:4])}" if targeted_users else "Anonymous targets",
                        ],
                        related_recs=failures,
                    )

        # -------------------------------------------------------------
        # RULE 3: Unusual Login Frequency
        # -------------------------------------------------------------
        for user, u_recs in user_events.items():
            if len(u_recs) >= max(15, avg_events_per_user * 3.0):
                add_or_merge_alert(
                    key=f"RULE3_USER_{user}",
                    alert_type="UNUSUAL_FREQUENCY",
                    severity="MEDIUM",
                    risk_score=60.0,
                    user=user,
                    ip=u_recs[0].get("ip"),
                    country=u_recs[0].get("country"),
                    message=f"Unusual event activity frequency for user '{user}'",
                    reasons=[
                        f"User generated {len(u_recs)} events ({len(u_recs) / max(1, avg_events_per_user):.1f}x higher than baseline)",
                        "Abnormal interaction volume compared to peer activity",
                    ],
                    related_recs=u_recs,
                )

        # -------------------------------------------------------------
        # RULE 4: Multiple Countries (Impossible Travel / Geo Anomaly)
        # -------------------------------------------------------------
        for user, u_recs in user_events.items():
            countries = list({r.get("country") for r in u_recs if r.get("country")})
            if len(countries) >= 2:
                # Check time difference between different countries
                first_seen = u_recs[0]["timestamp"]
                last_seen = u_recs[-1]["timestamp"]
                delta_hours = (last_seen - first_seen).total_seconds() / 3600.0
                if delta_hours <= 4.0:
                    add_or_merge_alert(
                        key=f"RULE4_GEO_{user}",
                        alert_type="MULTI_COUNTRY",
                        severity="HIGH",
                        risk_score=85.0,
                        user=user,
                        ip=u_recs[0].get("ip"),
                        country=", ".join(countries),
                        message=f"Impossible travel geo-anomaly detected for user '{user}'",
                        reasons=[
                            f"User authenticated from {len(countries)} different countries: {', '.join(countries)}",
                            f"Activity occurred across jurisdictions within {delta_hours:.1f} hours",
                        ],
                        related_recs=u_recs,
                    )

        # -------------------------------------------------------------
        # RULE 5: IP Anomaly (Password Spraying / Multi-Account Activity)
        # -------------------------------------------------------------
        for ip, ip_recs in ip_events.items():
            distinct_users = list({r.get("user") for r in ip_recs if r.get("user")})
            if len(distinct_users) >= 3:
                failures = [r for r in ip_recs if r.get("status") == "FAILURE"]
                severity = "HIGH" if len(failures) >= 2 else "MEDIUM"
                add_or_merge_alert(
                    key=f"RULE5_SPRAY_{ip}",
                    alert_type="IP_ANOMALY",
                    severity=severity,
                    risk_score=78.0,
                    user="multiple_accounts",
                    ip=ip,
                    country=ip_recs[0].get("country"),
                    message=f"Potential password spray / multi-account anomaly from IP {ip}",
                    reasons=[
                        f"Single IP address probed {len(distinct_users)} distinct user accounts: {', '.join(distinct_users[:5])}",
                        f"Total events from IP: {len(ip_recs)} ({len(failures)} failures)",
                    ],
                    related_recs=ip_recs,
                )

        # -------------------------------------------------------------
        # RULE 6: High Error Rate (> 60% failure with >= 3 attempts)
        # -------------------------------------------------------------
        for user, u_recs in user_events.items():
            if len(u_recs) >= 3:
                fails = sum(1 for r in u_recs if r.get("status") == "FAILURE")
                fail_rate = (fails / len(u_recs)) * 100.0
                if fail_rate >= 60.0 and len(u_recs) >= 3:
                    add_or_merge_alert(
                        key=f"RULE6_ERR_{user}",
                        alert_type="HIGH_ERROR_RATE",
                        severity="MEDIUM" if fail_rate < 80 else "HIGH",
                        risk_score=68.0 if fail_rate < 80 else 76.0,
                        user=user,
                        ip=u_recs[0].get("ip"),
                        country=u_recs[0].get("country"),
                        message=f"Elevated failure rate ({fail_rate:.0f}%) detected for user '{user}'",
                        reasons=[
                            f"{fails} out of {len(u_recs)} authentication attempts failed ({fail_rate:.1f}%)",
                            "Exceeds normal authentication failure tolerance",
                        ],
                        related_recs=u_recs,
                    )

        # -------------------------------------------------------------
        # RULE 7: Event Spike (Burst of events in 2-minute bucket)
        # -------------------------------------------------------------
        for bucket, b_recs in time_windows.items():
            if len(b_recs) >= 8:
                primary_user = b_recs[0].get("user")
                primary_ip = b_recs[0].get("ip")
                add_or_merge_alert(
                    key=f"RULE7_SPIKE_{bucket}",
                    alert_type="EVENT_SPIKE",
                    severity="MEDIUM",
                    risk_score=64.0,
                    user=primary_user,
                    ip=primary_ip,
                    country=b_recs[0].get("country"),
                    message=f"Sudden authentication event volume spike ({len(b_recs)} events in 2m)",
                    reasons=[
                        f"Traffic spike: {len(b_recs)} events recorded within a single 2-minute interval",
                        f"Occurred around window {bucket}",
                    ],
                    related_recs=b_recs,
                )

        # -------------------------------------------------------------
        # RULE 8: Suspicious Event Types & Security Signals
        # -------------------------------------------------------------
        suspicious_keywords = ["admin", "root", "mimikatz", "dump", "elevat", "privilege", "inject", "4720", "4728"]
        for rec in sorted_records:
            e_type = str(rec.get("event_type") or "").lower()
            u_name = str(rec.get("user") or "").lower()
            if any(k in e_type for k in suspicious_keywords) or any(k in u_name for k in ["admin", "administrator", "root"]):
                if rec.get("status") == "FAILURE":
                    add_or_merge_alert(
                        key=f"RULE8_SUSP_{rec.get('user')}_{rec.get('ip')}",
                        alert_type="SUSPICIOUS_EVENT",
                        severity="HIGH",
                        risk_score=75.0,
                        user=rec.get("user"),
                        ip=rec.get("ip"),
                        country=rec.get("country"),
                        message=f"Suspicious security event or privileged account access: {rec.get('event_type')}",
                        reasons=[
                            f"Sensitive event or account '{rec.get('user')}' targeted: {rec.get('event_type')}",
                            "Privileged security signal violation",
                        ],
                        related_recs=[rec],
                    )

        # -------------------------------------------------------------
        # RULE 9: High Severity Records (from input CSV)
        # -------------------------------------------------------------
        for rec in sorted_records:
            sev = rec.get("severity")
            if sev in ("CRITICAL", "HIGH"):
                add_or_merge_alert(
                    key=f"RULE9_SEV_{rec.get('user')}_{rec.get('ip')}",
                    alert_type="HIGH_SEVERITY_RECORD",
                    severity=sev,
                    risk_score=90.0 if sev == "CRITICAL" else 75.0,
                    user=rec.get("user"),
                    ip=rec.get("ip"),
                    country=rec.get("country"),
                    message=f"High-severity record imported from CSV for {rec.get('user') or rec.get('ip')}",
                    reasons=[
                        f"Record explicitly tagged with severity '{sev}'",
                        f"Event type: {rec.get('event_type')} (Status: {rec.get('status')})",
                    ],
                    related_recs=[rec],
                )

        # -------------------------------------------------------------
        # RULE 10: Repeated Suspicious Behavior (Compound escalation)
        # -------------------------------------------------------------
        # Check entities with multiple distinct alerts and escalate
        entity_alerts = defaultdict(list)
        for a in alerts_map.values():
            if a["user"]:
                entity_alerts[a["user"]].append(a)
            if a["ip"] and a["ip"] != "0.0.0.0":
                entity_alerts[a["ip"]].append(a)

        for entity, al_list in entity_alerts.items():
            if len(al_list) >= 2:
                # Compound escalation to CRITICAL / HIGH
                for a in al_list:
                    a["risk_score"] = min(100.0, a["risk_score"] + 12.0)
                    if a["severity"] in ("MEDIUM", "HIGH"):
                        a["severity"] = "CRITICAL" if a["risk_score"] >= 80 else "HIGH"
                    if "Compound security risk: Multiple concurrent threat indicators triggered" not in a["reasons"]:
                        a["reasons"].append(
                            f"Compound security risk: {len(al_list)} concurrent detection rules triggered for {entity}"
                        )

        # Return alerts sorted by risk score descending
        return sorted(list(alerts_map.values()), key=lambda a: a["risk_score"], reverse=True)
