"""
Flexible CSV Column Detector
============================
Automatically detects common security log fields using alias matching,
case-insensitive fuzzy normalization, and pattern recognition.
Preserves unknown columns so data is never silently lost.
"""

import re
from typing import Dict, List, Tuple, Set


CANONICAL_ALIASES: Dict[str, List[str]] = {
    "user": [
        "user", "username", "user_name", "account", "account_name", "accountname",
        "email", "user_id", "userid", "subject_user_name", "caller_user_name",
        "target_user", "principal", "user_email", "name", "actor", "login", "identity",
        "subject", "client", "member", "usr", "user_account"
    ],
    "ip": [
        "ip", "ip_address", "ipaddress", "source_ip", "sourceip", "src_ip",
        "srcip", "client_ip", "clientip", "remote_ip", "remoteip", "host_ip",
        "caller_ip", "origin_ip", "network_ip", "ip_addr", "address", "src",
        "client_address", "remote_host"
    ],
    "timestamp": [
        "timestamp", "time", "datetime", "date_time", "date", "event_time",
        "event_timestamp", "eventtime", "log_time", "logtime", "@timestamp",
        "created_at", "utc_time", "occurred_at", "ts", "timestamp_utc",
        "access_time", "login_time", "record_time", "start_time", "time_stamp",
        "event_date", "log_date", "event_datetime", "time_generated", "timegenerated",
        "time_created", "timecreated", "date_time_utc", "datetime_utc", "date_utc",
        "generation_time", "creation_time", "date_and_time", "dateandtime", "log_date_time",
        "logged_at", "occurred", "detected_at", "auth_time", "system_time", "epoch"
    ],
    "event_type": [
        "event_type", "eventtype", "event", "activity", "action", "event_name",
        "eventname", "event_id", "eventid", "type", "operation", "action_name",
        "category", "description", "event_description"
    ],
    "status": [
        "status", "result", "outcome", "success", "auth_result", "logon_status",
        "login_status", "response_code", "return_code", "verdict", "state"
    ],
    "severity": [
        "severity", "risk", "priority", "level", "severity_level", "risk_level",
        "alert_level", "threat_level"
    ],
    "country": [
        "country", "location", "geo", "region", "country_name", "country_code",
        "geo_location", "geolocation", "source_country", "city"
    ],
    "computer": [
        "computer", "target_computer", "targetcomputer", "host", "hostname",
        "workstation", "machine", "destination_host", "device", "endpoint"
    ],
}


class ColumnDetector:
    """Detects and maps CSV headers to canonical security event fields."""

    @staticmethod
    def _normalize_header(header: str) -> str:
        """Strip spaces, BOM, special punctuation, and convert to lowercase for comparison."""
        if not header:
            return ""
        s = str(header).strip().lstrip("\ufeff").lower()
        # Replace spaces, dashes, dots, slashes, backslashes with underscore
        s = re.sub(r"[\s\-\.\/\\]+", "_", s)
        # Remove parentheses, brackets, quotes, colons, etc.
        s = re.sub(r"[^\w]", "", s)
        return s.strip("_")

    @classmethod
    def detect_columns(cls, raw_headers: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Detects canonical mappings from raw headers.

        Args:
            raw_headers: List of headers read directly from the CSV

        Returns:
            Tuple of:
            - detected: dict mapping {canonical_field: raw_header_name}
            - unmapped: list of raw headers that did not match any canonical alias
        """
        detected: Dict[str, str] = {}
        matched_headers: Set[str] = set()

        cleaned_headers = [(h, cls._normalize_header(h)) for h in raw_headers if h]

        # 1. Exact canonical alias match
        for canonical, aliases in CANONICAL_ALIASES.items():
            for orig, norm in cleaned_headers:
                if norm in aliases and canonical not in detected and orig not in matched_headers:
                    detected[canonical] = orig
                    matched_headers.add(orig)
                    break

        # 2. Substring fallback match if not already found
        for canonical, aliases in CANONICAL_ALIASES.items():
            if canonical in detected:
                continue
            for orig, norm in cleaned_headers:
                if orig in matched_headers:
                    continue
                # If any alias is contained inside the normalized header
                for alias in aliases:
                    if len(alias) >= 3 and alias in norm:
                        detected[canonical] = orig
                        matched_headers.add(orig)
                        break
                if canonical in detected:
                    break

        unmapped = [h for h in raw_headers if h and h not in matched_headers]

        return detected, unmapped
