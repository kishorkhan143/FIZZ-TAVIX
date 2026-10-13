"""Unit tests for Policy Engine rules, transitions, and auditing."""

import pytest
from unittest.mock import MagicMock, patch

from labguard_ssh.audit import AuditLogger
from labguard_ssh.config import SSHModuleSettings
from labguard_ssh.models import (
    ActionResponse,
    AllowlistApplyRequest,
    AuditResult,
    DisableSSHRequest,
    PolicyMode,
    PolicyUpdateRequest,
)
from labguard_ssh.policy_engine import PolicyEngine
from labguard_ssh.service_controller import ControllerSecurityError


@pytest.fixture
def engine(tmp_path):
    audit_path = tmp_path / "test_audit.log"
    settings = SSHModuleSettings(
        ssh_policy=PolicyMode.MONITOR_ONLY,
        allow_privileged_operations=True,
        audit_log_path=str(audit_path),
    )
    audit_logger = AuditLogger(log_path=str(audit_path))
    return PolicyEngine(settings=settings, audit_logger=audit_logger)


def test_default_policy_is_monitor_only(engine):
    """Engine starts in MONITOR_ONLY by default."""
    status = engine.get_policy_status()
    assert status.configured_policy == PolicyMode.MONITOR_ONLY


def test_policy_change_executes_no_system_actions(engine):
    """Policy transition does not automatically stop SSH or touch firewall."""
    with patch.object(engine.controller, "disable_ssh_service") as mock_disable, \
         patch.object(engine.controller, "apply_allowlist") as mock_fw:

        req = PolicyUpdateRequest(policy=PolicyMode.DISABLE_SSH)
        status = engine.set_policy(req, operator="admin_user")

        assert status.configured_policy == PolicyMode.DISABLE_SSH
        mock_disable.assert_not_called()
        mock_fw.assert_not_called()

        # Check audit log recorded the transition
        recent = engine.audit.get_recent(5)
        assert len(recent) >= 1
        assert recent[-1].operation == "UPDATE_POLICY"
        assert recent[-1].result == AuditResult.SUCCESS
        assert recent[-1].details["new_policy"] == "DISABLE_SSH"


def test_monitor_only_blocks_disable_ssh(engine):
    """Attempting to disable SSH while in MONITOR_ONLY mode must be rejected."""
    req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=True)

    with pytest.raises(ControllerSecurityError, match="Current policy is MONITOR_ONLY"):
        engine.disable_ssh(req, operator="test_user")

    recent = engine.audit.get_recent(5)
    assert recent[-1].operation == "DISABLE_SSH"
    assert recent[-1].result == AuditResult.REJECTED
    assert recent[-1].error_category == "POLICY_VIOLATION"


def test_disable_ssh_allowed_in_disable_ssh_policy(engine):
    """Authorized disable operation proceeds in DISABLE_SSH policy mode."""
    engine.current_policy = PolicyMode.DISABLE_SSH

    mock_resp = ActionResponse(
        success=True,
        operation="DISABLE_SSH",
        message="Service stopped",
        warnings=[],
        details={"uninstalled": False},
        timestamp="2026-10-12T12:00:00Z",
    )

    with patch.object(engine.controller, "disable_ssh_service", return_value=mock_resp):
        req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=True)
        resp = engine.disable_ssh(req, operator="admin")
        assert resp.success is True

        recent = engine.audit.get_recent(5)
        assert recent[-1].operation == "DISABLE_SSH"
        assert recent[-1].result == AuditResult.SUCCESS


def test_apply_allowlist_blocked_in_monitor_only_unless_dry_run(engine):
    """Live allowlist application is blocked in MONITOR_ONLY, but dry-run is allowed."""
    # Dry run should pass
    dry_req = AllowlistApplyRequest(
        confirm=True,
        recovery_method_confirmed=True,
        allowed_ips=["192.168.1.5"],
        dry_run=True,
    )
    with patch.object(engine.controller, "apply_allowlist", return_value=ActionResponse(
        success=True,
        operation="ALLOWLIST_DRY_RUN",
        message="Dry run ok",
        warnings=[],
        details={},
        timestamp="2026-10-12T12:00:00Z"
    )):
        resp = engine.apply_allowlist(dry_req)
        assert resp.success is True

    # Live application should fail in MONITOR_ONLY
    live_req = AllowlistApplyRequest(
        confirm=True,
        recovery_method_confirmed=True,
        allowed_ips=["192.168.1.5"],
        dry_run=False,
    )
    with pytest.raises(ControllerSecurityError, match="Firewall modifications are not permitted in MONITOR_ONLY"):
        engine.apply_allowlist(live_req)
