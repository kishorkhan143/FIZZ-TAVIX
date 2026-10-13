"""Unit tests for Windows OpenSSH Detection Engine with mocked PowerShell responses."""

import os
import pytest
from unittest.mock import MagicMock, patch

from labguard_ssh.detector import SSHDetector
from labguard_ssh.models import ServiceState, StartupState
from labguard_ssh.windows_detector import WindowsSSHDetector


@pytest.fixture
def win_detector(tmp_path):
    """Fixture providing WindowsSSHDetector with temporary config paths."""
    config_file = tmp_path / "sshd_config"
    config_dir = tmp_path / "sshd_config.d"
    config_dir.mkdir()
    return WindowsSSHDetector(
        service_names=["sshd"],
        config_file=str(config_file),
        config_dir=str(config_dir),
    )


def test_windows_package_installed_capability_success(win_detector):
    """Verify detection when WindowsCapability reports OpenSSH.Server is Installed."""
    mock_json = {"State": "Installed", "Name": "OpenSSH.Server~~~~0.0.1.0"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")), \
         patch.object(win_detector, "_get_sshd_binary_version", return_value="9.5p1"):
        installed, version = win_detector.check_package_installed()
        assert installed is True
        assert version == "9.5p1"


def test_windows_package_not_installed(win_detector):
    """Verify detection when WindowsCapability reports NotPresent and binary is absent."""
    mock_json = {"State": "NotPresent", "Name": "OpenSSH.Server~~~~0.0.1.0"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")), \
         patch.object(win_detector, "_get_sshd_binary_version", return_value=None):
        installed, version = win_detector.check_package_installed()
        assert installed is False
        assert version is None


def test_windows_package_installed_binary_fallback(win_detector):
    """Verify fallback to sshd.exe binary version when capability query returns empty."""
    with patch.object(win_detector, "run_powershell_json", return_value=(1, None, "Access denied")), \
         patch.object(win_detector, "_get_sshd_binary_version", return_value="9.2p1"):
        installed, version = win_detector.check_package_installed()
        assert installed is True
        assert version == "9.2p1"


def test_windows_discover_service_name_found(win_detector):
    """Verify discovery finds existing 'sshd' Windows service."""
    mock_json = {"Name": "sshd"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        name, exists = win_detector.discover_service_name()
        assert name == "sshd"
        assert exists is True


def test_windows_discover_service_name_missing(win_detector):
    """Verify discovery reports exists=False when sshd service is missing."""
    with patch.object(win_detector, "run_powershell_json", return_value=(0, None, "")):
        name, exists = win_detector.discover_service_name()
        assert name == "sshd"
        assert exists is False


def test_windows_check_service_status_active_string(win_detector):
    """Verify active status with PowerShell string 'Running'."""
    mock_json = {"Status": "Running", "Name": "sshd"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        state, is_active = win_detector.check_service_status("sshd")
        assert state == ServiceState.ACTIVE
        assert is_active is True


def test_windows_check_service_status_active_numeric(win_detector):
    """Verify active status with PowerShell ServiceControllerStatus numeric 4."""
    mock_json = {"Status": 4, "Name": "sshd"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        state, is_active = win_detector.check_service_status("sshd")
        assert state == ServiceState.ACTIVE
        assert is_active is True


def test_windows_check_service_status_inactive(win_detector):
    """Verify inactive status with PowerShell 'Stopped' or 1."""
    mock_json = {"Status": "Stopped", "Name": "sshd"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        state, is_active = win_detector.check_service_status("sshd")
        assert state == ServiceState.INACTIVE
        assert is_active is False


def test_windows_check_service_status_not_found(win_detector):
    """Verify not-found status when Get-Service returns null."""
    with patch.object(win_detector, "run_powershell_json", return_value=(1, None, "Service not found")):
        state, is_active = win_detector.check_service_status("sshd")
        assert state == ServiceState.NOT_FOUND
        assert is_active is False


def test_windows_check_service_enabled_automatic(win_detector):
    """Verify enabled status with PowerShell 'Automatic' or 2."""
    mock_json = {"StartType": "Automatic"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        state, is_enabled = win_detector.check_service_enabled("sshd")
        assert state == StartupState.ENABLED
        assert is_enabled is True


def test_windows_check_service_disabled(win_detector):
    """Verify disabled status with PowerShell 'Disabled' or 4."""
    mock_json = {"StartType": "Disabled"}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        state, is_enabled = win_detector.check_service_enabled("sshd")
        assert state == StartupState.DISABLED
        assert is_enabled is False


def test_windows_check_listening_ports_single(win_detector):
    """Verify parsing Get-NetTCPConnection single object response."""
    mock_json = {"LocalAddress": "0.0.0.0", "LocalPort": 22, "OwningProcess": 4096}
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        ports = win_detector.check_listening_ports(configured_port=22)
        assert len(ports) == 1
        assert ports[0].port == 22
        assert ports[0].address == "0.0.0.0"
        assert "4096" in (ports[0].process or "")


def test_windows_check_listening_ports_multiple(win_detector):
    """Verify parsing Get-NetTCPConnection list of objects."""
    mock_json = [
        {"LocalAddress": "0.0.0.0", "LocalPort": 22, "OwningProcess": 4096},
        {"LocalAddress": "::", "LocalPort": 22, "OwningProcess": 4096},
    ]
    with patch.object(win_detector, "run_powershell_json", return_value=(0, mock_json, "")):
        ports = win_detector.check_listening_ports(configured_port=22)
        assert len(ports) == 2
        assert ports[0].address == "0.0.0.0"
        assert ports[1].address == "::"


def test_ssh_detector_windows_integration(tmp_path):
    """Verify unified SSHDetector delegates to Windows detection when is_windows=True."""
    cfg_file = tmp_path / "sshd_config"
    cfg_file.write_text("Port 22\nPermitRootLogin no\nPasswordAuthentication yes\n")

    detector = SSHDetector(
        config_file=str(cfg_file),
        is_windows=True,
    )
    assert detector.is_windows is True
    assert detector.windows_detector is not None

    with patch.object(detector.windows_detector, "check_package_installed", return_value=(True, "9.5p1")), \
         patch.object(detector.windows_detector, "discover_service_name", return_value=("sshd", True)), \
         patch.object(detector.windows_detector, "check_service_status", return_value=(ServiceState.ACTIVE, True)), \
         patch.object(detector.windows_detector, "check_service_enabled", return_value=(StartupState.ENABLED, True)), \
         patch.object(detector.windows_detector, "check_listening_ports", return_value=[]):

        report = detector.get_full_report()
        assert report.package_installed is True
        assert report.package_version == "9.5p1"
        assert report.service_name == "sshd"
        assert report.service_active is True
        assert report.service_state == ServiceState.ACTIVE
        assert report.service_enabled is True
        assert report.startup_state == StartupState.ENABLED
        assert report.config.permit_root_login == "no"
        assert report.config.password_authentication == "yes"


def test_windows_check_listening_ports_netstat_fallback(win_detector):
    """Verify listening port detection via netstat fallback when Get-NetTCPConnection fails."""
    mock_netstat = (
        "  Proto  Local Address          Foreign Address        State           PID\n"
        "  TCP    0.0.0.0:22             0.0.0.0:0              LISTENING       1234\n"
        "  TCP    0.0.0.0:80             0.0.0.0:0              LISTENING       5678\n"
    )
    # Get-NetTCPConnection returns error/empty, netstat returns output
    with patch.object(win_detector, "run_powershell_json", return_value=(1, None, "Cmdlet not found")), \
         patch.object(win_detector, "run_safe_powershell", return_value=(0, mock_netstat, "")):
        ports = win_detector.check_listening_ports(configured_port=22)
        assert len(ports) == 1
        assert ports[0].port == 22
        assert ports[0].address == "0.0.0.0"
        assert "1234" in (ports[0].process or "")


def test_windows_parse_ssh_configuration(win_detector, tmp_path):
    """Verify safe parsing of Windows sshd_config without exposing credentials."""
    cfg_file = tmp_path / "sshd_config"
    cfg_file.write_text(
        "Port 2222\n"
        "PermitRootLogin no\n"
        "PasswordAuthentication yes\n"
        "PubkeyAuthentication yes\n"
        "X11Forwarding no\n"
        "MaxAuthTries 5\n"
    )
    win_detector.config_file = str(cfg_file)
    summary = win_detector.parse_ssh_configuration()

    assert summary.port == 2222
    assert summary.permit_root_login == "no"
    assert summary.password_authentication == "yes"
    assert summary.pubkey_authentication == "yes"
    assert summary.x11_forwarding == "no"
    assert summary.max_auth_tries == 5
    assert str(cfg_file) in summary.config_files_inspected


def test_windows_sanitize_service_name_blocks_injection(win_detector):
    """Verify malicious service names containing PowerShell injection tokens are rejected."""
    malicious_names = [
        "sshd'; Remove-Item C:\\",
        "sshd | Stop-Process",
        "sshd & calc.exe",
        "sshd`whoami`",
    ]
    with patch.object(win_detector, "run_powershell_json") as mock_ps:
        for mal_name in malicious_names:
            state, active = win_detector.check_service_status(mal_name)
            assert state == ServiceState.NOT_FOUND
            assert active is False

            start_state, enabled = win_detector.check_service_enabled(mal_name)
            assert start_state == StartupState.NOT_FOUND
            assert enabled is False

        # PowerShell query should never have been invoked with malicious arguments
        mock_ps.assert_not_called()


def test_windows_check_listening_ports_port_validation(win_detector):
    """Verify configured_port validates bounds (falls back to 22 if invalid)."""
    with patch.object(win_detector, "run_powershell_json", return_value=(0, [], "")) as mock_ps:
        win_detector.check_listening_ports(configured_port=99999)  # Out of range port
        # Verify query was called with port 22
        called_query = mock_ps.call_args[0][0]
        assert "-LocalPort 22" in called_query


