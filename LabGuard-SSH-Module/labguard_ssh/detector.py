"""SSH Detection Engine for LabGuard SSH Module.

Inspects OpenSSH installation, systemd service state, listening network sockets,
and SSH configuration without requiring administrator privileges or modifying the system.
"""

from __future__ import annotations

import datetime
import glob
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from labguard_ssh.models import (
    SSHConfigSummary,
    SSHListeningPort,
    SSHStatusReport,
    ServiceState,
    StartupState,
)
from labguard_ssh.macos_detector import MacOSSSHDetector
from labguard_ssh.windows_detector import WindowsSSHDetector

logger = logging.getLogger("labguard_ssh.detector")


class SSHDetector:
    """Safe, read-only detector for OpenSSH on Linux (Ubuntu/Debian), macOS (Darwin), and Windows systems."""

    def __init__(
        self,
        service_names: Optional[List[str]] = None,
        config_file: Optional[str] = None,
        config_dir: Optional[str] = None,
        is_windows: Optional[bool] = None,
        is_macos: Optional[bool] = None,
    ):
        self.is_windows = (sys.platform == "win32") if is_windows is None else is_windows
        self.is_macos = (sys.platform == "darwin") if is_macos is None else is_macos

        if self.is_windows:
            self.service_names = service_names or ["sshd"]
            program_data = os.environ.get("ProgramData", r"C:\ProgramData")
            self.config_file = config_file or os.path.join(program_data, "ssh", "sshd_config")
            self.config_dir = config_dir or os.path.join(program_data, "ssh", "sshd_config.d")
            self.windows_detector = WindowsSSHDetector(
                service_names=self.service_names,
                config_file=self.config_file,
                config_dir=self.config_dir,
            )
            self.macos_detector = None
        elif self.is_macos:
            self.service_names = service_names or ["com.openssh.sshd", "ssh"]
            self.config_file = config_file or "/etc/ssh/sshd_config"
            self.config_dir = config_dir or "/etc/ssh/sshd_config.d"
            self.windows_detector = None
            self.macos_detector = MacOSSSHDetector(
                service_names=self.service_names,
                config_file=self.config_file,
                config_dir=self.config_dir,
            )
        else:
            self.service_names = service_names or ["ssh", "sshd"]
            self.config_file = config_file or "/etc/ssh/sshd_config"
            self.config_dir = config_dir or "/etc/ssh/sshd_config.d"
            self.windows_detector = None
            self.macos_detector = None

    def run_safe_cmd(self, args: List[str], timeout: float = 3.0) -> Tuple[int, str, str]:
        """Execute a command safely using an argument list, shell=False, and strict timeout."""
        try:
            res = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                shell=False,
                check=False,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out: %s", " ".join(args))
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return 127, "", f"Binary not found: {args[0]}"
        except Exception as e:
            logger.error("Command error for %s: %s", " ".join(args), e)
            return -1, "", str(e)

    def check_package_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if openssh-server package is installed."""
        if self.is_windows and self.windows_detector:
            return self.windows_detector.check_package_installed()
        if self.is_macos and self.macos_detector:
            return self.macos_detector.check_package_installed()

        if shutil.which("dpkg-query"):
            code, stdout, _ = self.run_safe_cmd(
                ["dpkg-query", "-W", "-f=${Status} ${Version}\n", "openssh-server"]
            )
            if code == 0 and "install ok installed" in stdout:
                parts = stdout.split()
                version = parts[-1] if len(parts) >= 4 else None
                return True, version

        # Fallback for systems where dpkg-query is not available or non-Debian
        if shutil.which("sshd"):
            code, _, stderr = self.run_safe_cmd(["sshd", "-V"])
            # sshd -V usually writes version string to stderr
            output = stderr or ""
            match = re.search(r"OpenSSH_([^\s,]+)", output)
            version = match.group(1) if match else "installed (sshd binary found)"
            return True, version

        return False, None

    def discover_service_name(self) -> Tuple[str, bool]:
        """Find the matching active or existing unit name from candidate service names."""
        if self.is_windows and self.windows_detector:
            return self.windows_detector.discover_service_name()
        if self.is_macos and self.macos_detector:
            return self.macos_detector.discover_service_name()

        if not shutil.which("systemctl"):
            return self.service_names[0], False

        for candidate in self.service_names:
            code, stdout, _ = self.run_safe_cmd(
                ["systemctl", "list-unit-files", f"{candidate}.service"]
            )
            if code == 0 and f"{candidate}.service" in stdout:
                return candidate, True

        # Check if systemctl status finds it even if unit file not listed in list-unit-files
        for candidate in self.service_names:
            code, stdout, stderr = self.run_safe_cmd(["systemctl", "status", f"{candidate}.service"])
            combined = (stdout + " " + stderr).lower()
            if "could not be found" in combined or "not found" in combined or "not-found" in combined or code == 4:
                continue
            if code in (0, 3) or "loaded: loaded" in combined or "loaded: masked" in combined:
                return candidate, True

        return self.service_names[0], False

    def check_service_status(self, service_name: str) -> Tuple[ServiceState, bool]:
        """Check current runtime state of the SSH service unit."""
        if self.is_windows and self.windows_detector:
            return self.windows_detector.check_service_status(service_name)
        if self.is_macos and self.macos_detector:
            return self.macos_detector.check_service_status(service_name)

        if not shutil.which("systemctl"):
            return ServiceState.UNKNOWN, False

        code, stdout, _ = self.run_safe_cmd(["systemctl", "is-active", f"{service_name}.service"])
        stdout_lower = stdout.lower()

        if stdout_lower == "active":
            return ServiceState.ACTIVE, True
        elif stdout_lower == "inactive":
            return ServiceState.INACTIVE, False
        elif stdout_lower == "failed":
            return ServiceState.FAILED, False
        elif "could not be found" in stdout_lower or code == 4:
            return ServiceState.NOT_FOUND, False
        else:
            return ServiceState.UNKNOWN, False

    def check_service_enabled(self, service_name: str) -> Tuple[StartupState, bool]:
        """Check whether the SSH service is enabled to launch at system boot."""
        if self.is_windows and self.windows_detector:
            return self.windows_detector.check_service_enabled(service_name)
        if self.is_macos and self.macos_detector:
            return self.macos_detector.check_service_enabled(service_name)

        if not shutil.which("systemctl"):
            return StartupState.UNKNOWN, False

        code, stdout, _ = self.run_safe_cmd(["systemctl", "is-enabled", f"{service_name}.service"])
        stdout_lower = stdout.lower()

        if "enabled" in stdout_lower:
            return StartupState.ENABLED, True
        elif "disabled" in stdout_lower:
            return StartupState.DISABLED, False
        elif "static" in stdout_lower:
            return StartupState.STATIC, False
        elif "masked" in stdout_lower:
            return StartupState.MASKED, False
        elif "not-found" in stdout_lower or code == 4:
            return StartupState.NOT_FOUND, False
        else:
            return StartupState.UNKNOWN, False

    def check_listening_ports(self, configured_port: Optional[int] = None) -> List[SSHListeningPort]:
        """Safely determine if SSH is listening on network sockets."""
        if self.is_windows and self.windows_detector:
            return self.windows_detector.check_listening_ports(configured_port)
        if self.is_macos and self.macos_detector:
            return self.macos_detector.check_listening_ports(configured_port)

        results: List[SSHListeningPort] = []

        if shutil.which("ss"):
            code, stdout, _ = self.run_safe_cmd(["ss", "-tlnp"])
            # Fall back to ss -tln if unprivileged user lacks process view
            if code != 0 or not stdout:
                code, stdout, _ = self.run_safe_cmd(["ss", "-tln"])

            if code == 0 and stdout:
                for line in stdout.splitlines():
                    # Look for SSH either by process name 'sshd' or matching standard port 22/configured_port
                    is_ssh_socket = False
                    process_name = None

                    if "sshd" in line:
                        is_ssh_socket = True
                        process_name = "sshd"

                    # Parse local address and port column
                    # Formats:
                    # 'tcp LISTEN 0 128 0.0.0.0:22 ...' or 'LISTEN 0 128 0.0.0.0:22 ...'
                    parts = line.split()
                    if "LISTEN" in parts:
                        listen_idx = parts.index("LISTEN")
                        if len(parts) > listen_idx + 3:
                            local_addr_col = parts[listen_idx + 3]
                            if ":" in local_addr_col:
                                addr_part, port_part = local_addr_col.rsplit(":", 1)
                                try:
                                    port_num = int(port_part)
                                    target_port = configured_port or 22
                                    if port_num == target_port or is_ssh_socket:
                                        # Normalize address
                                        clean_addr = addr_part.strip("[]")
                                        if clean_addr == "*":
                                            clean_addr = "0.0.0.0"
                                        # Avoid duplicate entries
                                        if not any(r.port == port_num and r.address == clean_addr for r in results):
                                            results.append(
                                                SSHListeningPort(
                                                    port=port_num,
                                                    address=clean_addr,
                                                    protocol="tcp",
                                                    process=process_name or ("sshd" if port_num == 22 else None),
                                                )
                                            )
                                except ValueError:
                                    pass

        return results

    def parse_ssh_configuration(self) -> SSHConfigSummary:
        """Safely parse OpenSSH server configuration files without leaking credentials."""
        if self.is_windows and self.windows_detector:
            return self.windows_detector.parse_ssh_configuration()
        if self.is_macos and self.macos_detector:
            return self.macos_detector.parse_ssh_configuration()

        config_files_to_read: List[str] = []

        if os.path.isfile(self.config_file):
            config_files_to_read.append(self.config_file)

        if os.path.isdir(self.config_dir):
            drop_ins = sorted(glob.glob(os.path.join(self.config_dir, "*.conf")))
            config_files_to_read.extend(drop_ins)

        summary = SSHConfigSummary(config_files_inspected=config_files_to_read)

        # In OpenSSH, first match typically wins for sshd_config options
        extracted: Dict[str, str] = {}

        for filepath in config_files_to_read:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue

                        # Directives: 'PermitRootLogin no' or 'PermitRootLogin=no'
                        tokens = stripped.split(None, 1)
                        if not tokens:
                            continue
                        key = tokens[0].lower()
                        val = tokens[1].strip().strip('"').strip("'") if len(tokens) > 1 else ""

                        if key not in extracted:
                            extracted[key] = val
            except (IOError, PermissionError) as e:
                logger.warning("Could not read SSH config file %s: %s", filepath, e)

        # Populate structured attributes
        if "permitrootlogin" in extracted:
            summary.permit_root_login = extracted["permitrootlogin"]

        if "passwordauthentication" in extracted:
            summary.password_authentication = extracted["passwordauthentication"].lower()

        if "pubkeyauthentication" in extracted:
            summary.pubkey_authentication = extracted["pubkeyauthentication"].lower()

        if "port" in extracted:
            try:
                summary.port = int(extracted["port"])
            except ValueError:
                pass

        if "x11forwarding" in extracted:
            summary.x11_forwarding = extracted["x11forwarding"].lower()

        if "maxauthtries" in extracted:
            try:
                summary.max_auth_tries = int(extracted["maxauthtries"])
            except ValueError:
                pass

        return summary

    def get_full_report(self) -> SSHStatusReport:
        """Aggregate all detection signals into a structured status report."""
        pkg_installed, pkg_version = self.check_package_installed()
        service_name, service_exists = self.discover_service_name()
        service_state, is_active = self.check_service_status(service_name)
        startup_state, is_enabled = self.check_service_enabled(service_name)
        config_summary = self.parse_ssh_configuration()
        listening_ports = self.check_listening_ports(configured_port=config_summary.port)

        return SSHStatusReport(
            package_installed=pkg_installed,
            package_version=pkg_version,
            service_exists=service_exists,
            service_name=service_name,
            service_active=is_active,
            service_state=service_state,
            service_enabled=is_enabled,
            startup_state=startup_state,
            listening_ports=listening_ports,
            config=config_summary,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
