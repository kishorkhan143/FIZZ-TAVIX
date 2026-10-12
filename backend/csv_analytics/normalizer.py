"""
Data Normalization & Sanitization Engine
========================================
Normalizes raw CSV rows into structured, strongly-typed security event dicts.
Quarantines malformed or unparseable rows with precise reasons.
Never silently discards data.
"""

import re
import ipaddress
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dateutil import parser as date_parser

# Supported explicit timestamp formats for fast-path parsing
EXPLICIT_TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y/%m/%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%Y-%m-%d",
]

SUCCESS_STATUS_VALUES = {
    "success", "successful", "succeeded", "ok", "0", "4624", "pass", "allowed",
    "allow", "true", "yes", "authorized", "granted"
}

FAILURE_STATUS_VALUES = {
    "failure", "failed", "fail", "1", "4625", "error", "denied", "deny",
    "block", "blocked", "false", "no", "unauthorized", "rejected"
}


class DataNormalizer:
    """Normalizes and validates rows extracted from an uploaded CSV."""

    @staticmethod
    def parse_timestamp(val: Any) -> Optional[datetime]:
        """Parse timestamp flexibly into timezone-aware UTC datetime."""
        if val is None:
            return None
        s = str(val).strip()
        if not s or s.lower() in ("null", "none", "nan", "undefined", "-", "n/a"):
            return None

        # Check for numeric unix timestamp (seconds or milliseconds)
        try:
            if s.isdigit() or (s.replace(".", "", 1).isdigit() and len(s) >= 10):
                numeric_val = float(s)
                # If milliseconds (e.g. > 1e11)
                if numeric_val > 1e11:
                    numeric_val /= 1000.0
                return datetime.fromtimestamp(numeric_val, tz=timezone.utc)
        except Exception:
            pass

        # Try fast-path formats
        for fmt in EXPLICIT_TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt
            except ValueError:
                continue

        # Flexible fallback with dateutil parser
        try:
            dt = date_parser.parse(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            return None

    @staticmethod
    def normalize_status(status_raw: Any, event_type_raw: Any = None) -> Tuple[str, str]:
        """
        Normalize status and infer event_type if needed.
        Returns: (status: 'SUCCESS'|'FAILURE'|'UNKNOWN', event_type: str)
        """
        s_val = str(status_raw or "").strip().lower()
        e_val = str(event_type_raw or "").strip().upper()

        if s_val in SUCCESS_STATUS_VALUES:
            status = "SUCCESS"
        elif s_val in FAILURE_STATUS_VALUES:
            status = "FAILURE"
        elif "success" in s_val:
            status = "SUCCESS"
        elif "fail" in s_val or "err" in s_val or "den" in s_val:
            status = "FAILURE"
        else:
            # Check event_type if status is ambiguous or empty
            e_lower = e_val.lower()
            if "fail" in e_lower or "error" in e_lower or "4625" in e_lower:
                status = "FAILURE"
            elif "success" in e_lower or "4624" in e_lower:
                status = "SUCCESS"
            else:
                status = "SUCCESS" if not s_val else s_val.upper()

        event_type = e_val if e_val else ("LOGIN_FAILURE" if status == "FAILURE" else "LOGIN_SUCCESS")
        return status, event_type

    @staticmethod
    def normalize_ip(ip_raw: Any) -> Optional[str]:
        """Clean and validate IP address (IPv4 or IPv6)."""
        if ip_raw is None:
            return None
        s = str(ip_raw).strip()
        if not s or s.lower() in ("null", "none", "nan", "-", "unknown", "n/a"):
            return None

        # Clean port if present e.g., "192.168.1.20:443"
        clean_s = s
        if ":" in s and s.count(":") == 1:
            clean_s = s.split(":")[0]

        try:
            ipaddress.ip_address(clean_s)
            return clean_s
        except ValueError:
            return None

    @classmethod
    def normalize_record(
        cls,
        row_idx: int,
        raw_row: Dict[str, Any],
        mapping: Dict[str, str],
        unmapped_keys: List[str],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Normalizes a single raw row using the detected column mapping.

        Returns:
            (valid_dict, None) if row is valid, or
            (None, quarantine_dict) if row is invalid/unparseable.
        """
        # Extract fields using mapping
        user_header = mapping.get("user")
        ip_header = mapping.get("ip")
        ts_header = mapping.get("timestamp")
        event_header = mapping.get("event_type")
        status_header = mapping.get("status")
        country_header = mapping.get("country")
        computer_header = mapping.get("computer")
        severity_header = mapping.get("severity")

        raw_user = raw_row.get(user_header) if user_header else None
        raw_ip = raw_row.get(ip_header) if ip_header else None
        raw_event = raw_row.get(event_header) if event_header else None
        raw_status = raw_row.get(status_header) if status_header else None
        raw_country = raw_row.get(country_header) if country_header else None
        raw_computer = raw_row.get(computer_header) if computer_header else None
        raw_severity = raw_row.get(severity_header) if severity_header else None

        # Check if row is completely empty
        if not any(str(v).strip() for v in raw_row.values() if v is not None and str(v).strip() != ""):
            return None, {
                "row_number": row_idx,
                "reason": "Empty row",
                "raw_data": {k: str(v) for k, v in raw_row.items() if v is not None},
            }

        # 1. Identity validation (user and/or IP)
        user = str(raw_user).strip() if raw_user is not None else ""
        if user.lower() in ("null", "none", "nan", "-", "undefined", "unknown"):
            user = ""

        ip = cls.normalize_ip(raw_ip) or ""

        # If both user and IP are missing, check if an IP can be found in other columns
        if not user and not ip:
            for k, v in raw_row.items():
                if v and k not in (ts_header, status_header, event_header, severity_header):
                    cand_ip = cls.normalize_ip(v)
                    if cand_ip:
                        ip = cand_ip
                        break

        if not user and not ip:
            return None, {
                "row_number": row_idx,
                "reason": "Missing both user and IP address (at least one is required)",
                "raw_data": {k: str(v) for k, v in raw_row.items() if v is not None},
            }

        # 2. Flexible Timestamp Resolution
        ts = None
        if ts_header and ts_header in raw_row:
            raw_ts_val = raw_row.get(ts_header)
            if (
                raw_ts_val is not None
                and str(raw_ts_val).strip()
                and str(raw_ts_val).strip().lower() not in ("null", "none", "nan", "undefined", "-")
            ):
                ts = cls.parse_timestamp(raw_ts_val)
                if ts is None:
                    return None, {
                        "row_number": row_idx,
                        "reason": f"Invalid or missing timestamp: '{raw_ts_val}'",
                        "raw_data": {k: str(v) for k, v in raw_row.items() if v is not None},
                    }
            else:
                # Value in timestamp column is empty or None
                for col_name, col_val in raw_row.items():
                    if col_val and col_name != ts_header:
                        cand_ts = cls.parse_timestamp(col_val)
                        if cand_ts is not None:
                            ts = cand_ts
                            break
                if ts is None:
                    return None, {
                        "row_number": row_idx,
                        "reason": f"Invalid or missing timestamp: '{raw_ts_val}'",
                        "raw_data": {k: str(v) for k, v in raw_row.items() if v is not None},
                    }
        else:
            # No timestamp column was specified or present in CSV
            for col_name, col_val in raw_row.items():
                if col_val:
                    cand_ts = cls.parse_timestamp(col_val)
                    if cand_ts is not None:
                        ts = cand_ts
                        break
            if ts is None:
                from datetime import timedelta
                ts = datetime.now(timezone.utc) - timedelta(seconds=max(0, 3600 - row_idx * 10))

        # 3. Status and event type normalization
        status, event_type = cls.normalize_status(raw_status, raw_event)

        # 4. Optional metadata fields
        country = str(raw_country).strip() if raw_country else None
        if country and country.lower() in ("null", "none", "-", "unknown"):
            country = None

        computer = str(raw_computer).strip() if raw_computer else None
        if computer and computer.lower() in ("null", "none", "-"):
            computer = None

        severity = str(raw_severity).strip().upper() if raw_severity else None
        if severity and severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
            severity = None

        # 5. Collect extra unmapped fields safely
        extra = {}
        for k in unmapped_keys:
            val = raw_row.get(k)
            if val is not None and str(val).strip() != "":
                extra[k] = str(val).strip()

        valid_dict = {
            "row_number": row_idx,
            "timestamp": ts,
            "user": user or (f"ip_{ip}" if ip else "anonymous"),
            "ip": ip or "0.0.0.0",
            "target_computer": computer,
            "event_type": event_type,
            "status": status,
            "country": country,
            "severity": severity,
            "extra_fields": extra,
        }

        return valid_dict, None
