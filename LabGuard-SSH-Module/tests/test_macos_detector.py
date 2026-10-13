"""Unit and integration tests for macOS OpenSSH detection.

Clearly distinguishes between:
1. Mocked tests that simulate macOS command outputs (safe on any OS).
2. Live integration tests that safely inspect the real macOS host (Darwin only).
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

from labguard_ssh.config import SSHModuleSettings
from labguard_ssh.detector import SSHDetector
from labguard_ssh.macos_detector import MacOSSSHDetector
from labguard_ssh.models import DisableSSHRequest, ServiceState, StartupState
from labguard_ssh.service_controller import ControllerSecurityError, SSHServiceController


# =========================================================================
# SECTION 1: MOCKED MACOS UNIT TESTS (Safe to run on Linux, Mac, or Windows)
# =========================================================================

@pytest.fixture
def mock_mac_detector(tmp_path):
    """Fixture providing a MacOSSSHDetector instance with isolated temporary paths."""
    config_file = tmp_path / "sshd_config"
    config_file.write_text("Port 22\nPermitRootLogin no\nPasswordAuthentication yes\n")
    config_dir = tmp_path / "sshd_config.d"
    config_dir.mkdir()
    return MacOSSSHDetector(
        service_names=["com.openssh.sshd", "ssh"],
        config_file=str(config_file),
        config_dir=str(config_dir),
    )


def test_mocked_macos_package_installed_success(mock_mac_detector):
    """[MOCKED] Verify macOS package detection from OpenSSH binary output."""
    with patch("shutil.which", return_value="/usr/bin/ssh"), \
         patch("os.path.exists", return_value=True), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(0, "", "OpenSSH_9.9p1, LibreSSL 3.3.6")):
        installed, version = mock_mac_detector.check_package_installed()
        assert installed is True
        assert version == "9.9p1"


def test_mocked_macos_package_missing(mock_mac_detector):
    """[MOCKED] Verify package detection reports False when ssh/sshd binaries are absent."""
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=False):
        installed, version = mock_mac_detector.check_package_installed()
        assert installed is False
        assert version is None


def test_mocked_macos_discover_service_plist_found(mock_mac_detector):
    """[MOCKED] Verify service discovery locates macOS launchd ssh.plist."""
    with patch("os.path.isfile", side_effect=lambda p: p == "/System/Library/LaunchDaemons/ssh.plist"):
        name, exists = mock_mac_detector.discover_service_name()
        assert name == "com.openssh.sshd"
        assert exists is True


def test_mocked_macos_discover_service_missing(mock_mac_detector):
    """[MOCKED] Verify service discovery handles missing plist and missing launchd entry."""
    with patch("os.path.isfile", return_value=False), \
         patch("shutil.which", return_value="/bin/launchctl"), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(113, "", "Could not find service")):
        name, exists = mock_mac_detector.discover_service_name()
        assert name == "com.openssh.sshd"
        assert exists is False


def test_mocked_macos_service_enabled_via_launchctl(mock_mac_detector):
    """[MOCKED] Verify detection of enabled Remote Login service via launchctl list (code 0)."""
    with patch("shutil.which", return_value="/bin/launchctl"), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(0, "{\n\t\"LimitLoadToSessionType\" = \"System\";\n}\n", "")):
        state, is_enabled = mock_mac_detector.check_service_enabled("com.openssh.sshd")
        assert state == StartupState.ENABLED
        assert is_enabled is True


def test_mocked_macos_service_disabled_via_launchctl(mock_mac_detector):
    """[MOCKED] Verify detection of disabled Remote Login service via launchctl list (code 113)."""
    with patch("shutil.which", return_value="/bin/launchctl"), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(113, "", "Could not find service \"com.openssh.sshd\"")):
        state, is_enabled = mock_mac_detector.check_service_enabled("com.openssh.sshd")
        assert state == StartupState.DISABLED
        assert is_enabled is False


def test_mocked_macos_service_status_active_via_process(mock_mac_detector):
    """[MOCKED] Verify active status when sshd process is running via pgrep."""
    with patch.object(mock_mac_detector, "check_package_installed", return_value=(True, "9.9p1")), \
         patch.object(mock_mac_detector, "discover_service_name", return_value=("com.openssh.sshd", True)), \
         patch("shutil.which", return_value="/usr/bin/pgrep"), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(0, "12345", "")), \
         patch.object(mock_mac_detector, "check_listening_ports", return_value=[]):
        state, is_active = mock_mac_detector.check_service_status("com.openssh.sshd")
        assert state == ServiceState.ACTIVE
        assert is_active is True


def test_mocked_macos_service_status_inactive(mock_mac_detector):
    """[MOCKED] Verify inactive status when neither sshd process nor port 22 is active."""
    with patch.object(mock_mac_detector, "check_package_installed", return_value=(True, "9.9p1")), \
         patch.object(mock_mac_detector, "discover_service_name", return_value=("com.openssh.sshd", True)), \
         patch("shutil.which", return_value="/usr/bin/pgrep"), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(1, "", "")), \
         patch.object(mock_mac_detector, "check_listening_ports", return_value=[]):
        state, is_active = mock_mac_detector.check_service_status("com.openssh.sshd")
        assert state == ServiceState.INACTIVE
        assert is_active is False


def test_mocked_macos_listening_ports_netstat(mock_mac_detector):
    """[MOCKED] Verify parsing of macOS BSD netstat -an -p tcp output for port 22."""
    mock_netstat = (
        "Active Internet connections (including servers)\n"
        "Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)\n"
        "tcp4       0      0  *.22                   *.*                    LISTEN\n"
        "tcp6       0      0  *.22                   *.*                    LISTEN\n"
        "tcp4       0      0  127.0.0.1.8000         *.*                    LISTEN\n"
    )
    with patch("shutil.which", side_effect=lambda b: "/usr/sbin/netstat" if b == "netstat" else None), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(0, mock_netstat, "")):
        ports = mock_mac_detector.check_listening_ports(configured_port=22)
        assert len(ports) == 2
        ipv4_entry = next(p for p in ports if p.address == "0.0.0.0")
        assert ipv4_entry.port == 22
        assert ipv4_entry.protocol == "tcp"
        assert ipv4_entry.process == "sshd"


def test_mocked_macos_listening_ports_lsof(mock_mac_detector):
    """[MOCKED] Verify enrichment with lsof process information."""
    mock_lsof = (
        "COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
        "sshd    45123 root    3u  IPv4 0x1234      0t0  TCP *:22 (LISTEN)\n"
    )
    with patch("shutil.which", side_effect=lambda b: "/usr/sbin/lsof" if b == "lsof" else None), \
         patch.object(mock_mac_detector, "run_safe_cmd", return_value=(0, mock_lsof, "")):
        ports = mock_mac_detector.check_listening_ports(configured_port=22)
        assert len(ports) == 1
        assert ports[0].port == 22
        assert ports[0].process == "sshd"


def test_mocked_ssh_detector_macos_delegation(tmp_path):
    """[MOCKED] Verify SSHDetector properly delegates all calls to MacOSSSHDetector when on Darwin."""
    cfg_file = tmp_path / "sshd_config"
    cfg_file.write_text("Port 22\nPermitRootLogin no\n")

    detector = SSHDetector(
        config_file=str(cfg_file),
        is_macos=True,
        is_windows=False,
    )
    assert detector.is_macos is True
    assert detector.macos_detector is not None

    with patch.object(detector.macos_detector, "check_package_installed", return_value=(True, "10.2p1")), \
         patch.object(detector.macos_detector, "discover_service_name", return_value=("com.openssh.sshd", True)), \
         patch.object(detector.macos_detector, "check_service_status", return_value=(ServiceState.INACTIVE, False)), \
         patch.object(detector.macos_detector, "check_service_enabled", return_value=(StartupState.DISABLED, False)), \
         patch.object(detector.macos_detector, "check_listening_ports", return_value=[]):

        report = detector.get_full_report()
        assert report.package_installed is True
        assert report.package_version == "10.2p1"
        assert report.service_name == "com.openssh.sshd"
        assert report.service_exists is True
        assert report.service_active is False
        assert report.service_state == ServiceState.INACTIVE
        assert report.service_enabled is False
        assert report.startup_state == StartupState.DISABLED
        assert report.config.permit_root_login == "no"


# =========================================================================
# SECTION 2: LIVE REAL MAC INSPECTION TESTS (Darwin only, safe and read-only)
# =========================================================================

@pytest.mark.skipif(sys.platform != "darwin", reason="Live macOS inspection only executes on real macOS hosts")
def test_real_macos_inspection_live():
    """[REAL MAC] Safely inspect the actual local Mac environment without mocking.

    Guarantees:
    - Never executes modifying commands (no sudo, no launchctl load/unload, no systemsetup).
    - Checks real OpenSSH binaries on this Mac.
    - Accurately checks whether port 22 is listening.
    - Clearly distinguishes installed vs enabled vs running.
    """
    detector = SSHDetector()
    assert detector.is_macos is True

    report = detector.get_full_report()

    # OpenSSH client/server is built into macOS
    assert report.package_installed is True
    assert report.package_version is not None
    assert "p" in report.package_version or "installed" in report.package_version

    # macOS launchd service exists
    assert report.service_exists is True
    assert report.service_name == "com.openssh.sshd"

    # Enforce typed enums
    assert isinstance(report.service_state, ServiceState)
    assert isinstance(report.startup_state, StartupState)
    assert isinstance(report.service_active, bool)
    assert isinstance(report.service_enabled, bool)
    assert isinstance(report.listening_ports, list)

    # If port 22 is not listening, service_active must be False
    if len(report.listening_ports) == 0:
        # Note: If no sshd process and no listening port, active is False
        assert report.service_active is False
        assert report.service_state == ServiceState.INACTIVE


@pytest.mark.skipif(sys.platform != "darwin", reason="Live macOS inspection only executes on real macOS hosts")
def test_real_macos_client_server_distinction():
    """[REAL MAC] Verify client /usr/bin/ssh vs server /usr/sbin/sshd on this Mac."""
    # Client binary inspection
    client_bin = "/usr/bin/ssh"
    assert os.path.exists(client_bin), "macOS OpenSSH client should be installed at /usr/bin/ssh"

    # Server daemon binary inspection
    server_bin = "/usr/sbin/sshd"
    assert os.path.exists(server_bin), "macOS OpenSSH server should be installed at /usr/sbin/sshd"

    # System launch daemon plist definition inspection
    plist_path = "/System/Library/LaunchDaemons/ssh.plist"
    assert os.path.exists(plist_path), "macOS launchd ssh.plist should exist in /System/Library/LaunchDaemons"


def test_macos_controller_fails_safely_without_systemctl():
    """[MOCKED/MACOS] Verify controller raises ControllerSecurityError when systemctl is absent."""
    ctrl = SSHServiceController(settings=SSHModuleSettings(allow_privileged_operations=True))
    req = DisableSSHRequest(confirm=True, acknowledged_lockout_risk=True)

    with patch.object(ctrl, "is_root", return_value=True), \
         patch("sys.platform", "darwin"), \
         patch("shutil.which", side_effect=lambda b: None if b == "systemctl" else f"/bin/{b}"):
        with pytest.raises(ControllerSecurityError, match="systemctl binary not found"):
            ctrl.disable_ssh_service(req)


def test_macos_controller_safe_firewall_handling():
    """[MOCKED/MACOS] Verify allowlist planner handles lack of UFW/iptables safely without errors."""
    ctrl = SSHServiceController(settings=SSHModuleSettings(allow_privileged_operations=False))
    with patch("shutil.which", return_value=None):
        plan = ctrl.plan_allowlist(["192.168.1.10"], port=22)
        assert plan.firewall_type == "none"
        assert plan.safe_to_apply is False
        assert any("Neither UFW nor iptables were detected" in w for w in plan.warnings)

