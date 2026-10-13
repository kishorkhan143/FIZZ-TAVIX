"""Integration tests for FastAPI endpoints in LabGuard SSH module."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from labguard_ssh.api import create_app
from labguard_ssh.audit import AuditLogger
from labguard_ssh.config import SSHModuleSettings
from labguard_ssh.models import (
    ActionResponse,
    PolicyMode,
    SSHConfigSummary,
    SSHListeningPort,
    SSHStatusReport,
    ServiceState,
    StartupState,
)
from labguard_ssh.policy_engine import PolicyEngine


@pytest.fixture
def client(tmp_path):
    audit_path = tmp_path / "api_audit.log"
    settings = SSHModuleSettings(
        ssh_policy=PolicyMode.MONITOR_ONLY,
        admin_key="test-secret-key-123",
        allow_privileged_operations=True,
        audit_log_path=str(audit_path),
    )
    audit = AuditLogger(log_path=str(audit_path))
    engine = PolicyEngine(settings=settings, audit_logger=audit)
    app = create_app(settings=settings, engine=engine)
    return TestClient(app)


def test_get_status_endpoint(client):
    """GET /api/ssh/status returns structured SSH details."""
    mock_report = SSHStatusReport(
        package_installed=True,
        package_version="8.9p1",
        service_exists=True,
        service_name="ssh",
        service_active=True,
        service_state=ServiceState.ACTIVE,
        service_enabled=True,
        startup_state=StartupState.ENABLED,
        listening_ports=[
            SSHListeningPort(port=22, address="0.0.0.0", protocol="tcp", process="sshd")
        ],
        config=SSHConfigSummary(
            permit_root_login="prohibit-password",
            password_authentication="no",
            pubkey_authentication="yes",
            port=22,
        ),
        timestamp="2026-10-12T12:00:00Z",
    )

    with patch("labguard_ssh.detector.SSHDetector.get_full_report", return_value=mock_report):
        resp = client.get("/api/ssh/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["package_installed"] is True
        assert data["service_name"] == "ssh"
        assert data["service_active"] is True
        assert data["config"]["permit_root_login"] == "prohibit-password"
        assert len(data["listening_ports"]) == 1
        assert data["listening_ports"][0]["port"] == 22


def test_get_policy_endpoint(client):
    """GET /api/ssh/policy returns default MONITOR_ONLY."""
    resp = client.get("/api/ssh/policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured_policy"] == "MONITOR_ONLY"
    assert data["requires_admin_auth"] is True


def test_update_policy_unauthorized(client):
    """POST /api/ssh/policy without header is rejected with 401."""
    resp = client.post("/api/ssh/policy", json={"policy": "DISABLE_SSH"})
    assert resp.status_code == 401


def test_update_policy_authorized(client):
    """POST /api/ssh/policy with valid token updates policy."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.post(
        "/api/ssh/policy",
        json={"policy": "DISABLE_SSH"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["configured_policy"] == "DISABLE_SSH"


def test_update_policy_invalid_ip_fails(client):
    """POST /api/ssh/policy with malformed IP returns 422."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.post(
        "/api/ssh/policy",
        json={"policy": "ALLOWLIST", "allowed_ips": ["not-an-ip-address"]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_disable_ssh_missing_confirmation(client):
    """POST /api/ssh/actions/disable without confirm=true returns 400."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.post(
        "/api/ssh/actions/disable",
        json={"confirm": False, "acknowledged_lockout_risk": True},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "confirm=true" in resp.json()["detail"]


def test_disable_ssh_in_monitor_only_returns_409(client):
    """POST /api/ssh/actions/disable when in MONITOR_ONLY returns 409 Conflict."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.post(
        "/api/ssh/actions/disable",
        json={"confirm": True, "acknowledged_lockout_risk": True},
        headers=headers,
    )
    assert resp.status_code == 409
    assert "MONITOR_ONLY" in resp.json()["detail"]


def test_disable_ssh_success(client):
    """POST /api/ssh/actions/disable in DISABLE_SSH mode returns success and warnings."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}

    # First switch policy to DISABLE_SSH
    client.post("/api/ssh/policy", json={"policy": "DISABLE_SSH"}, headers=headers)

    mock_resp = ActionResponse(
        success=True,
        operation="DISABLE_SSH",
        message="Service stopped and disabled",
        warnings=[
            "CRITICAL WARNING: Stopping SSH will prevent NEW SSH connections immediately.",
            "Active established SSH sessions are NOT terminated automatically.",
        ],
        details={"uninstalled": False},
        timestamp="2026-10-12T12:00:00Z",
    )

    with patch("labguard_ssh.service_controller.SSHServiceController.disable_ssh_service", return_value=mock_resp):
        resp = client.post(
            "/api/ssh/actions/disable",
            json={"confirm": True, "acknowledged_lockout_risk": True, "reason": "Authorized lab test"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["warnings"]) >= 2
        assert any("new ssh connections" in w.lower() for w in data["warnings"])


def test_allowlist_dry_run_endpoint(client):
    """POST /api/ssh/actions/allowlist in dry-run mode returns proposals."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.post(
        "/api/ssh/actions/allowlist",
        json={
            "confirm": True,
            "recovery_method_confirmed": True,
            "allowed_ips": ["192.168.1.10/32"],
            "dry_run": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["operation"] == "ALLOWLIST_DRY_RUN"


def test_audit_endpoint(client):
    """GET /api/ssh/audit returns structured entries with X-LabGuard-Admin-Key header."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.get("/api/ssh/audit", headers=headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)


def test_audit_endpoint_bearer_auth(client):
    """GET /api/ssh/audit succeeds with standard Authorization: Bearer <token>."""
    headers = {"Authorization": "Bearer test-secret-key-123"}
    resp = client.get("/api/ssh/audit", headers=headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)


def test_audit_endpoint_bearer_lowercase(client):
    """GET /api/ssh/audit succeeds with lowercase Authorization: bearer <token>."""
    headers = {"Authorization": "bearer test-secret-key-123"}
    resp = client.get("/api/ssh/audit", headers=headers)
    assert resp.status_code == 200


def test_audit_endpoint_unauthorized_returns_401(client):
    """GET /api/ssh/audit without credentials returns 401 and WWW-Authenticate: Bearer header."""
    resp = client.get("/api/ssh/audit")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"
    assert "Invalid or missing" in resp.json()["detail"]


def test_audit_endpoint_invalid_bearer_returns_401(client):
    """GET /api/ssh/audit with invalid Bearer token returns 401."""
    headers = {"Authorization": "Bearer invalid-wrong-token"}
    resp = client.get("/api/ssh/audit", headers=headers)
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


def test_record_and_retrieve_audit_event_via_api(client):
    """Verify safe, non-destructive audit event recording (setting MONITOR_ONLY) and retrieval."""
    headers = {"Authorization": "Bearer test-secret-key-123"}

    # 1. Initially, verify audit returns an empty list
    init_resp = client.get("/api/ssh/audit", headers=headers)
    assert init_resp.status_code == 200
    assert init_resp.json() == []

    # 2. Perform safe, non-destructive policy confirmation keeping MONITOR_ONLY
    update_resp = client.post(
        "/api/ssh/policy",
        json={"policy": "MONITOR_ONLY"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["configured_policy"] == "MONITOR_ONLY"

    # 3. Retrieve audit events and verify the event was recorded and returned
    audit_resp = client.get("/api/ssh/audit", headers=headers)
    assert audit_resp.status_code == 200
    entries = audit_resp.json()
    assert len(entries) == 1
    assert entries[0]["operation"] == "UPDATE_POLICY"
    assert entries[0]["policy"] == "MONITOR_ONLY"
    assert entries[0]["result"] == "SUCCESS"
    assert "timestamp" in entries[0]


def test_allowlist_live_in_monitor_only_returns_409(client):
    """POST /api/ssh/actions/allowlist with dry_run=False in MONITOR_ONLY returns 409 Conflict."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.post(
        "/api/ssh/actions/allowlist",
        json={
            "confirm": True,
            "recovery_method_confirmed": True,
            "allowed_ips": ["192.168.1.10/32"],
            "dry_run": False,
        },
        headers=headers,
    )
    assert resp.status_code == 409
    assert "MONITOR_ONLY" in resp.json()["detail"]


def test_arbitrary_shell_injection_in_api_rejected(client):
    """Verify malicious shell payloads in allowed_ips are strictly rejected with 422."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    malicious_payloads = [
        "127.0.0.1; reboot",
        "10.0.0.1 && cat /etc/shadow",
        "1.1.1.1 | rm -rf /",
        "`whoami`",
    ]
    for payload in malicious_payloads:
        resp = client.post(
            "/api/ssh/actions/allowlist",
            json={
                "confirm": True,
                "recovery_method_confirmed": True,
                "allowed_ips": [payload],
                "dry_run": True,
            },
            headers=headers,
        )
        assert resp.status_code == 422


def test_invalid_policy_name_rejected_by_api(client):
    """Verify arbitrary policy names are rejected with 422."""
    headers = {"X-LabGuard-Admin-Key": "test-secret-key-123"}
    resp = client.post(
        "/api/ssh/policy",
        json={"policy": "EXECUTE_ARBITRARY_COMMAND"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_get_status_endpoint_target_windows_success(client):
    """GET /api/ssh/status?target=windows returns validated Windows report."""
    mock_win_report = SSHStatusReport(
        package_installed=True,
        package_version="OpenSSH_9.5p1",
        service_exists=True,
        service_name="sshd",
        service_active=True,
        service_state=ServiceState.ACTIVE,
        service_enabled=True,
        startup_state=StartupState.ENABLED,
        listening_ports=[
            SSHListeningPort(port=22, address="0.0.0.0", protocol="tcp", process="sshd (PID 4012)")
        ],
        config=SSHConfigSummary(permit_root_login="no", password_authentication="yes", port=22),
        timestamp="2026-10-12T12:00:00Z",
    )

    with patch("labguard_ssh.remote_collector.RemoteSSHCollector.collect_status", return_value=mock_win_report):
        resp = client.get("/api/ssh/status?target=windows")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service_name"] == "sshd"
        assert data["service_active"] is True
        assert data["package_version"] == "OpenSSH_9.5p1"


def test_get_status_endpoint_target_windows_unconfigured(client):
    """GET /api/ssh/status?target=windows returns 400 when unconfigured."""
    from labguard_ssh.remote_collector import RemoteCollectorError
    with patch(
        "labguard_ssh.remote_collector.RemoteSSHCollector.collect_status",
        side_effect=RemoteCollectorError("Windows agent URL is not configured (set LABGUARD_WINDOWS_AGENT_URL).")
    ):
        resp = client.get("/api/ssh/status?target=windows")
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"]


def test_get_status_endpoint_target_windows_unreachable(client):
    """GET /api/ssh/status?target=windows returns 503 when remote agent times out/unreachable."""
    from labguard_ssh.remote_collector import RemoteCollectorError
    with patch(
        "labguard_ssh.remote_collector.RemoteSSHCollector.collect_status",
        side_effect=RemoteCollectorError("Failed to connect to Windows agent at http://100.x.y.z:8001.")
    ):
        resp = client.get("/api/ssh/status?target=windows")
        assert resp.status_code == 503
        assert "Failed to connect" in resp.json()["detail"]


def test_get_status_endpoint_target_windows_auth_failed(client):
    """GET /api/ssh/status?target=windows returns 502 when remote agent rejects token."""
    from labguard_ssh.remote_collector import RemoteCollectorError
    with patch(
        "labguard_ssh.remote_collector.RemoteSSHCollector.collect_status",
        side_effect=RemoteCollectorError("Authentication failed: Windows agent rejected the bearer token.")
    ):
        resp = client.get("/api/ssh/status?target=windows")
        assert resp.status_code == 502
        assert "Authentication failed" in resp.json()["detail"]


