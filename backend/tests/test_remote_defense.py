"""
AuthSentinel -- Integration Tests for Remote Defense & Laptop A Telemetry
========================================================================
Validates:
1. Laptop A LAN IP collection and propagation to events and alerts.
2. High-risk anomalous login detection triggering alerts with Laptop A IP and hostname.
3. Admin Action 1: "lock_screen" -> RemoteCommand queued -> Collector polls -> Acknowledged.
4. Admin Action 2: "authorize" -> Alert marked AUTHORIZED and resolved (no disruptive command).
5. Admin Action 3: "shutdown" -> RemoteCommand queued -> Collector polls -> Acknowledged.
6. Collector helper logic (get_local_ip, parse_event IP injection).
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from fastapi import HTTPException

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, ROOT_DIR)

from database import SessionLocal, init_db
from models import RemoteCommand, Alert, AuthEvent
from schemas import EventIngestionRequest, AlertActionRequest, CommandAckRequest
from config import settings
import smtp_service
async def _mock_smtp(*args, **kwargs):
    return True
smtp_service.send_incident_alert_async = _mock_smtp

from main import (
    ingest_event,
    execute_alert_action,
    get_collector_commands,
    ack_collector_command,
    _local_date_utc_range,
    detection,
)

COLLECTOR_SECRET = settings.collector_secret


def setup_module():
    init_db()


async def run_laptop_ip_and_alert_test():
    """Verify Laptop A LAN IP is preserved and high-risk alert contains host & IP."""
    db = SessionLocal()
    try:
        # Clear existing alerts, events, and detection windows
        db.query(RemoteCommand).delete()
        db.query(Alert).delete()
        db.query(AuthEvent).delete()
        db.commit()
        detection._windows.clear()
        detection._success_alerted.clear()

        laptop_ip = "192.168.1.105"
        hostname = "LAPTOP-A"
        username = "admin_target"

        # Ingest 5 failed logon attempts to trigger REPEATED_FAILURE (HIGH risk)
        for i in range(5):
            req = EventIngestionRequest(
                event_id=4625,
                timestamp=datetime.now(timezone.utc),
                username=username,
                source_ip="127.0.0.1",   # Local Windows Event log artifact
                laptop_ip=laptop_ip,      # Collected real LAN IP
                source_host=hostname,
                target_computer=hostname,
                logon_type=2,
                logon_type_description="Interactive",
                status="FAILURE",
            )
            await ingest_event(body=req, db=db, _=None, x_source_label=hostname)

        # Check alerts created in DB
        alerts = db.query(Alert).order_by(Alert.id.desc()).all()
        assert len(alerts) >= 1, "Should have created at least 1 alert"

        high_alert = alerts[0]
        assert high_alert.risk_level in ("HIGH", "CRITICAL"), f"Expected HIGH/CRITICAL, got {high_alert.risk_level}"
        assert high_alert.source_host == hostname
        assert high_alert.source_ip == laptop_ip, f"Expected {laptop_ip}, got {high_alert.source_ip}"
        assert high_alert.username == username

        print(f"[PASS] Successfully detected anomalous login: Alert #{high_alert.id} ({high_alert.risk_level}) with IP {high_alert.source_ip} on {high_alert.source_host}")
        return high_alert.id, hostname
    finally:
        db.close()


async def run_admin_lock_screen_test():
    """Verify admin clicking 'Lock Screen' queues command and collector can poll and ack it."""
    alert_id, hostname = await run_laptop_ip_and_alert_test()
    db = SessionLocal()
    try:
        # 1. Admin triggers 'lock_screen'
        req = AlertActionRequest(
            action="lock_screen",
            terminal_id=hostname,
            note="Admin locked workstation on Laptop A",
        )
        action_res = await execute_alert_action(alert_id=alert_id, body=req, db=db)
        assert action_res["ok"] is True
        assert action_res["action"] == "lock_screen"

        # Verify alert status updated to REMEDIATING
        alert = db.get(Alert, alert_id)
        assert alert.status == "REMEDIATING"
        assert alert.resolved is False

        # 2. Collector polls for pending commands for LAPTOP-A
        commands = await get_collector_commands(
            terminal_id=hostname,
            x_source_label=hostname,
            x_collector_secret=COLLECTOR_SECRET,
            db=db,
        )
        assert len(commands) >= 1
        target_cmd = next((c for c in commands if c["command"] == "lock_screen"), None)
        assert target_cmd is not None
        cmd_id = target_cmd["id"]

        # 3. Collector acknowledges execution
        ack_req = CommandAckRequest(
            status="EXECUTED",
            message="Workstation screen locked successfully via user32.LockWorkStation",
        )
        ack_res = await ack_collector_command(
            command_id=cmd_id,
            body=ack_req,
            x_collector_secret=COLLECTOR_SECRET,
            db=db,
        )
        assert ack_res["ok"] is True
        assert ack_res["status"] == "EXECUTED"

        # 4. Verify in DB
        cmd_record = db.get(RemoteCommand, cmd_id)
        assert cmd_record.status == "EXECUTED"
        assert "locked" in cmd_record.result_message.lower()
        db.refresh(alert)
        assert alert.status == "RESOLVED"
        assert alert.resolved is True
        print(f"[PASS] Lock Screen action flow passed: Command #{cmd_id} queued, polled, and ACKed as EXECUTED.")
    finally:
        db.close()


async def run_admin_authorize_test():
    """Verify admin clicking 'Authorize' marks alert AUTHORIZED and resolved (no disruptive action)."""
    alert_id, hostname = await run_laptop_ip_and_alert_test()
    db = SessionLocal()
    try:
        # Admin clicks Authorize ("No problem / Benign")
        req = AlertActionRequest(
            action="authorize",
            terminal_id=hostname,
            note="Admin verified activity - legitimate user (No problem)",
        )
        res = await execute_alert_action(alert_id=alert_id, body=req, db=db)
        assert res["ok"] is True
        assert res["status"] == "AUTHORIZED"

        # Verify alert status in DB
        alert = db.get(Alert, alert_id)
        assert alert.status == "AUTHORIZED"
        assert alert.resolved is True
        assert "[ADMIN ACTION:" in alert.reason

        # Ensure no intrusive commands were queued
        commands = await get_collector_commands(
            terminal_id=hostname,
            x_source_label=hostname,
            x_collector_secret=COLLECTOR_SECRET,
            db=db,
        )
        assert len(commands) == 0

        print(f"[PASS] Authorize ('No problem') action flow passed: Alert #{alert_id} marked AUTHORIZED, no commands dispatched.")
    finally:
        db.close()


async def run_admin_shutdown_test():
    """Verify admin clicking 'Shutdown' queues command for remote power-off and can be ACKed."""
    alert_id, hostname = await run_laptop_ip_and_alert_test()
    db = SessionLocal()
    try:
        # Admin clicks Shutdown
        req = AlertActionRequest(
            action="shutdown",
            terminal_id=hostname,
            note="Emergency shutdown ordered by SecOps",
        )
        res = await execute_alert_action(alert_id=alert_id, body=req, db=db)
        assert res["ok"] is True
        assert res["action"] == "shutdown"

        # Verify alert is REMEDIATING
        alert = db.get(Alert, alert_id)
        assert alert.status == "REMEDIATING"
        assert alert.resolved is False

        # Collector polls
        commands = await get_collector_commands(
            terminal_id=hostname,
            x_source_label=hostname,
            x_collector_secret=COLLECTOR_SECRET,
            db=db,
        )
        assert len(commands) >= 1
        shutdown_cmd = next((c for c in commands if c["command"] == "shutdown"), None)
        assert shutdown_cmd is not None
        cmd_id = shutdown_cmd["id"]

        # Collector ACKs before initiating shutdown
        ack_req = CommandAckRequest(
            status="EXECUTED",
            message="Shutdown initiated via Windows command: shutdown /s /f /t 5",
        )
        ack_res = await ack_collector_command(
            command_id=cmd_id,
            body=ack_req,
            x_collector_secret=COLLECTOR_SECRET,
            db=db,
        )
        assert ack_res["ok"] is True
        assert ack_res["status"] == "EXECUTED"

        cmd_record = db.get(RemoteCommand, cmd_id)
        assert cmd_record.status == "EXECUTED"
        db.refresh(alert)
        assert alert.status == "RESOLVED"
        assert alert.resolved is True
        print(f"[PASS] Shutdown action flow passed: Command #{cmd_id} queued, polled, and ACKed as EXECUTED.")
    finally:
        db.close()


async def run_missing_action_target_test():
    """Ensure remote actions fail rather than dispatching to an assumed machine."""
    db = SessionLocal()
    alert = Alert(
        alert_type="REPEATED_FAILURE",
        source_ip=None,
        source_host=None,
        target_computer=None,
        status="OPEN",
        resolved=False,
    )
    db.add(alert)
    db.commit()
    try:
        try:
            await execute_alert_action(
                alert_id=alert.id,
                body=AlertActionRequest(action="shutdown"),
                db=db,
            )
            raise AssertionError("An action without a target must be rejected")
        except HTTPException as error:
            assert error.status_code == 400
        assert db.query(RemoteCommand).filter(RemoteCommand.alert_id == alert.id).count() == 0
    finally:
        db.delete(alert)
        db.commit()
        db.close()


def test_local_date_uses_utc_boundaries_for_india():
    start_utc, end_utc = _local_date_utc_range("2026-10-12")
    assert start_utc == datetime(2026, 10, 11, 18, 30)
    assert end_utc == datetime(2026, 10, 12, 18, 30)
    try:
        _local_date_utc_range("2026-02-30")
        raise AssertionError("Invalid calendar dates must be rejected")
    except HTTPException as error:
        assert error.status_code == 400


def test_collector_ip_resolution_logic():
    """Verify Laptop A collector IP resolution and event augmentation logic."""
    from LAPTOP_PACKAGE_A.laptop_a_package.collector import get_local_ip, parse_event

    # Test get_local_ip
    lan_ip = get_local_ip("http://127.0.0.1:8000")
    assert lan_ip is not None
    assert len(lan_ip.split(".")) == 4, f"Invalid IP format: {lan_ip}"
    print(f"[PASS] Laptop A LAN IP detected: {lan_ip}")

    # Test parse_event logic with mock event
    class MockEvent:
        EventID = 4625
        RecordNumber = 9999
        TimeGenerated = datetime.now(timezone.utc)
        StringInserts = [""] * 25

    mock_event = MockEvent()
    mock_event.StringInserts[5] = "target_analyst"
    mock_event.StringInserts[6] = "WORKGROUP"
    mock_event.StringInserts[9] = "0xc000006a"
    mock_event.StringInserts[10] = "2"
    mock_event.StringInserts[19] = "-"  # Local / unrecorded IP in Windows Security log

    parsed = parse_event(mock_event, target_computer="LAPTOP-A", local_ip=lan_ip)
    assert parsed is not None
    assert parsed["laptop_ip"] == lan_ip
    # Because source_ip was "-", it falls back to local_ip
    assert parsed["source_ip"] == lan_ip
    assert parsed["username"] == "target_analyst"
    assert parsed["event_id"] == 4625
    print(f"[PASS] Event parsing successfully injected collected Laptop A LAN IP ({parsed['source_ip']}) into telemetry payload.")


if __name__ == "__main__":
    print("\n========================================================")
    print("RUNNING TAVIX-GUARD REMOTE DEFENSE & TELEMETRY TEST SUITE")
    print("========================================================\n")
    setup_module()
    asyncio.run(run_laptop_ip_and_alert_test())
    asyncio.run(run_admin_lock_screen_test())
    asyncio.run(run_admin_authorize_test())
    asyncio.run(run_admin_shutdown_test())
    asyncio.run(run_missing_action_target_test())
    test_local_date_uses_utc_boundaries_for_india()
    test_collector_ip_resolution_logic()
    print("\n========================================================")
    print("ALL REMOTE DEFENSE & TELEMETRY TESTS PASSED SUCCESSFULLY!")
    print("========================================================\n")
