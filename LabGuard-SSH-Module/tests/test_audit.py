"""Unit tests for structured audit logger and credential redaction."""

import json
import pytest
from labguard_ssh.audit import AuditLogger, sanitize_data
from labguard_ssh.models import AuditResult, PolicyMode


def test_sanitize_data_masks_sensitive_keys():
    """Verify recursive masking of passwords, secrets, tokens, and keys."""
    raw = {
        "user": "lab_admin",
        "password": "supersecretpassword123",
        "api_key": "sec_987654321",
        "authorization": "Bearer secret_jwt_token",
        "nested": {
            "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
            "safe_param": "value_42",
        },
        "list_items": [
            {"token": "xyz123"},
            {"safe_item": True},
        ]
    }

    sanitized = sanitize_data(raw)

    assert sanitized["user"] == "lab_admin"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["nested"]["private_key"] == "[REDACTED]"
    assert sanitized["nested"]["safe_param"] == "value_42"
    assert sanitized["list_items"][0]["token"] == "[REDACTED]"
    assert sanitized["list_items"][1]["safe_item"] is True


def test_audit_logger_writes_and_retrieves(tmp_path):
    """Verify audit logger writes structured JSON-lines and loads recent history."""
    log_file = tmp_path / "test_audit.log"
    logger = AuditLogger(log_path=str(log_file))

    entry = logger.log(
        operation="DISABLE_SSH",
        policy=PolicyMode.DISABLE_SSH,
        result=AuditResult.SUCCESS,
        operator="admin",
        client_ip="127.0.0.1",
        details={"reason": "routine_check", "password": "should_be_masked"},
    )

    assert entry.details["password"] == "[REDACTED]"
    assert entry.details["reason"] == "routine_check"

    # Verify persisted file
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["operation"] == "DISABLE_SSH"
    assert parsed["details"]["password"] == "[REDACTED]"

    # Verify in-memory buffer
    recent = logger.get_recent(10)
    assert len(recent) == 1
    assert recent[0].operation == "DISABLE_SSH"


def test_audit_logger_restores_from_disk_on_startup(tmp_path):
    """Verify a new AuditLogger instance loads historical records from disk on startup."""
    log_file = tmp_path / "persisted_audit.log"

    # Instance 1 writes an entry and goes out of scope (simulating app shutdown)
    logger1 = AuditLogger(log_path=str(log_file))
    logger1.log(
        operation="UPDATE_POLICY",
        policy=PolicyMode.MONITOR_ONLY,
        result=AuditResult.SUCCESS,
        operator="admin",
        client_ip="127.0.0.1",
        details={"status": "initialized"},
    )
    del logger1

    # Instance 2 starts up (simulating app restart)
    logger2 = AuditLogger(log_path=str(log_file))
    recent = logger2.get_recent(10)
    assert len(recent) == 1
    assert recent[0].operation == "UPDATE_POLICY"
    assert recent[0].policy == PolicyMode.MONITOR_ONLY
    assert recent[0].result == AuditResult.SUCCESS
