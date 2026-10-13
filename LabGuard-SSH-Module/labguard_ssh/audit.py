"""Audit logging module for LabGuard SSH Security Module.

Records security-critical operations, policy transitions, and system actions
in structured JSON format while strictly preventing credential leakage.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from labguard_ssh.models import AuditLogEntry, AuditResult, PolicyMode

logger = logging.getLogger("labguard_ssh.audit")

# Sensitive keys that must always be masked if encountered
SENSITIVE_KEY_PATTERNS = {
    "password", "passwd", "secret", "token", "private_key",
    "key", "authorization", "auth", "credential", "api_key"
}


def sanitize_data(data: Any) -> Any:
    """Recursively sanitize data to ensure no passwords or credentials are logged."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


class AuditLogger:
    """Thread-safe structured audit logger."""

    def __init__(self, log_path: str = "labguard_ssh_audit.log"):
        self.log_path = log_path
        self._lock = threading.Lock()
        self._recent_entries: List[AuditLogEntry] = []
        self._max_recent = 500
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load persisted audit log entries from disk into memory on startup."""
        if not os.path.isfile(self.log_path):
            return
        loaded: List[AuditLogEntry] = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        data = json.loads(stripped)
                        loaded.append(AuditLogEntry(**data))
                    except Exception as err:
                        logger.warning("Could not parse audit log entry from '%s': %s", self.log_path, err)
            with self._lock:
                self._recent_entries = loaded[-self._max_recent:]
        except Exception as e:
            logger.error("Failed to load audit entries from '%s': %s", self.log_path, e)

    def log(
        self,
        operation: str,
        policy: PolicyMode,
        result: AuditResult,
        operator: Optional[str] = None,
        client_ip: Optional[str] = None,
        error_category: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """Record an audit log entry in structured JSON format."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        clean_details = sanitize_data(details or {})

        entry = AuditLogEntry(
            timestamp=now_utc,
            operation=operation,
            policy=policy,
            result=result,
            operator=operator,
            client_ip=client_ip,
            error_category=error_category,
            details=clean_details,
        )

        json_line = json.dumps(entry.model_dump(), default=str)

        with self._lock:
            # Keep in-memory buffer for easy query/testing
            self._recent_entries.append(entry)
            if len(self._recent_entries) > self._max_recent:
                self._recent_entries.pop(0)

            # Persist to disk
            try:
                log_dir = os.path.dirname(self.log_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")
            except Exception as e:
                logger.error("Failed to write to audit log file '%s': %s", self.log_path, e)

        return entry

    def get_recent(self, limit: int = 50) -> List[AuditLogEntry]:
        """Retrieve the most recent audit entries from the in-memory log buffer."""
        with self._lock:
            return list(self._recent_entries[-limit:])


# Singleton instance
_audit_logger_instance: Optional[AuditLogger] = None
_instance_lock = threading.Lock()


def get_audit_logger(log_path: Optional[str] = None) -> AuditLogger:
    """Get or initialize the global AuditLogger."""
    global _audit_logger_instance
    with _instance_lock:
        if _audit_logger_instance is None or (log_path and _audit_logger_instance.log_path != log_path):
            from labguard_ssh.config import get_settings
            path = log_path or get_settings().audit_log_path
            _audit_logger_instance = AuditLogger(log_path=path)
        return _audit_logger_instance
