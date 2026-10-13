"""Unit tests for SSH detection engine with mocked system interactions."""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from labguard_ssh.detector import SSHDetector
from labguard_ssh.models import ServiceState, StartupState


@pytest.fixture
def detector(tmp_path):
    """Fixture providing an SSHDetector instance with temporary config paths."""
    config_file = tmp_path / "sshd_config"
    config_dir = tmp_path / "sshd_config.d"
    config_dir.mkdir()
    return SSHDetector(
        service_names=["ssh", "sshd"],
        config_file=str(config_file),
        config_dir=str(config_dir),
        is_macos=False,
        is_windows=False,
    )


def test_check_package_installed_dpkg_success(detector):
    """Verify dpkg-query detection of installed openssh-server."""
    with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
         patch.object(detector, "run_safe_cmd", return_value=(0, "install ok installed 1:8.9p1-3ubuntu0.6", "")):
        installed, version = detector.check_package_installed()
        assert installed is True
        assert version == "1:8.9p1-3ubuntu0.6"


def test_check_package_installed_dpkg_missing(detector):
    """Verify missing package detection when dpkg-query reports no package."""
    with patch("shutil.which", side_effect=lambda cmd: "/usr/bin/dpkg-query" if cmd == "dpkg-query" else None), \
         patch.object(detector, "run_safe_cmd", return_value=(1, "no packages found", "error")):
        installed, version = detector.check_package_installed()
        assert installed is False
        assert version is None


def test_check_package_installed_binary_fallback(detector):
    """Verify fallback to sshd binary version when dpkg-query is absent."""
    with patch("shutil.which", side_effect=lambda cmd: "/usr/sbin/sshd" if cmd == "sshd" else None), \
         patch.object(detector, "run_safe_cmd", return_value=(0, "", "OpenSSH_9.0p1, OpenSSL 3.0.2")):
        installed, version = detector.check_package_installed()
        assert installed is True
        assert version == "9.0p1"


def test_discover_service_name_found(detector):
    """Verify discovery finds existing 'ssh.service'."""
    with patch("shutil.which", return_value="/bin/systemctl"), \
         patch.object(detector, "run_safe_cmd", return_value=(0, "ssh.service enabled", "")):
        name, exists = detector.discover_service_name()
        assert name == "ssh"
        assert exists is True


def test_discover_service_name_missing(detector):
    """Verify discovery reports exists=False when neither ssh nor sshd exists."""
    with patch("shutil.which", return_value="/bin/systemctl"), \
         patch.object(detector, "run_safe_cmd", return_value=(1, "", "Unit not found")):
        name, exists = detector.discover_service_name()
        assert name == "ssh"
        assert exists is False


def test_check_service_status_active(detector):
    """Verify active service state detection."""
    with patch("shutil.which", return_value="/bin/systemctl"), \
         patch.object(detector, "run_safe_cmd", return_value=(0, "active", "")):
        state, is_active = detector.check_service_status("ssh")
        assert state == ServiceState.ACTIVE
        assert is_active is True


def test_check_service_status_inactive(detector):
    """Verify inactive service state detection."""
    with patch("shutil.which", return_value="/bin/systemctl"), \
         patch.object(detector, "run_safe_cmd", return_value=(3, "inactive", "")):
        state, is_active = detector.check_service_status("ssh")
        assert state == ServiceState.INACTIVE
        assert is_active is False


def test_check_service_status_not_found(detector):
    """Verify not-found service state detection."""
    with patch("shutil.which", return_value="/bin/systemctl"), \
         patch.object(detector, "run_safe_cmd", return_value=(4, "could not be found", "")):
        state, is_active = detector.check_service_status("ssh")
        assert state == ServiceState.NOT_FOUND
        assert is_active is False


def test_check_service_enabled_states(detector):
    """Verify systemctl is-enabled parsing."""
    with patch("shutil.which", return_value="/bin/systemctl"):
        with patch.object(detector, "run_safe_cmd", return_value=(0, "enabled", "")):
            state, enabled = detector.check_service_enabled("ssh")
            assert state == StartupState.ENABLED
            assert enabled is True

        with patch.object(detector, "run_safe_cmd", return_value=(1, "disabled", "")):
            state, enabled = detector.check_service_enabled("ssh")
            assert state == StartupState.DISABLED
            assert enabled is False

        with patch.object(detector, "run_safe_cmd", return_value=(1, "masked", "")):
            state, enabled = detector.check_service_enabled("ssh")
            assert state == StartupState.MASKED
            assert enabled is False


def test_check_listening_ports(detector):
    """Verify parsing ss output for SSH sockets."""
    mock_ss_output = (
        "Netid State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess\n"
        "tcp   LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:((\"sshd\",pid=1024,fd=3))\n"
        "tcp   LISTEN 0      128             [::]:22            [::]:*    users:((\"sshd\",pid=1024,fd=4))\n"
        "tcp   LISTEN 0      511          0.0.0.0:80         0.0.0.0:*    users:((\"nginx\",pid=2048,fd=6))\n"
    )
    with patch("shutil.which", return_value="/bin/ss"), \
         patch.object(detector, "run_safe_cmd", return_value=(0, mock_ss_output, "")):
        ports = detector.check_listening_ports(configured_port=22)
        assert len(ports) == 2
        assert ports[0].port == 22
        assert ports[0].address == "0.0.0.0"
        assert ports[0].process == "sshd"
        assert ports[1].port == 22
        assert ports[1].address == "::"


def test_parse_ssh_configuration(detector, tmp_path):
    """Verify safe parsing of sshd_config without exposing credentials."""
    cfg_file = tmp_path / "sshd_config"
    cfg_file.write_text(
        "# OpenSSH Daemon Configuration\n"
        "Port 2222\n"
        "PermitRootLogin prohibit-password\n"
        "PasswordAuthentication no\n"
        "PubkeyAuthentication yes\n"
        "X11Forwarding no\n"
        "MaxAuthTries 4\n"
        "# Commented sensitive line:\n"
        "# HostKey /etc/ssh/ssh_host_rsa_key\n"
    )

    summary = detector.parse_ssh_configuration()
    assert summary.port == 2222
    assert summary.permit_root_login == "prohibit-password"
    assert summary.password_authentication == "no"
    assert summary.pubkey_authentication == "yes"
    assert summary.x11_forwarding == "no"
    assert summary.max_auth_tries == 4
    assert str(cfg_file) in summary.config_files_inspected


def test_get_full_report_structure(detector):
    """Verify end-to-end status report generation."""
    with patch.object(detector, "check_package_installed", return_value=(True, "8.9p1")), \
         patch.object(detector, "discover_service_name", return_value=("ssh", True)), \
         patch.object(detector, "check_service_status", return_value=(ServiceState.ACTIVE, True)), \
         patch.object(detector, "check_service_enabled", return_value=(StartupState.ENABLED, True)), \
         patch.object(detector, "check_listening_ports", return_value=[]):

        report = detector.get_full_report()
        assert report.package_installed is True
        assert report.package_version == "8.9p1"
        assert report.service_exists is True
        assert report.service_active is True
        assert report.service_state == ServiceState.ACTIVE
        assert report.service_enabled is True
        assert report.startup_state == StartupState.ENABLED
        assert isinstance(report.timestamp, str)
