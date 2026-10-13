"""macOS OpenSSH Detection Engine for LabGuard SSH Module.

Provides safe, read-only inspection of OpenSSH Server on macOS (Darwin) systems
using standard macOS utilities (launchctl, netstat, lsof, pgrep).
Distinguishes between OpenSSH installed, enabled in launchd, and actively running.
Never modifies system configuration, stops services, or exposes credentials.
"""

from __future__ import annotations

import datetime
import glob
import logging
import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from labguard_ssh.models import (
    SSHConfigSummary,
    SSHListeningPort,
    SSHStatusReport,
    ServiceState,
    StartupState,
)

logger = logging.getLogger("labguard_ssh.macos_detector")


class MacOSSSHDetector:
    """Safe, read-only OpenSSH detector for macOS hosts."""

    DEFAULT_SERVICE_NAME = "com.openssh.sshd"
    LAUNCHD_PLIST_PATHS = [
        "/System/Library/LaunchDaemons/ssh.plist",
        "/System/Library/LaunchDaemons/com.openssh.sshd.plist",
        "/Library/LaunchDaemons/ssh.plist",
        "/Library/LaunchDaemons/com.openssh.sshd.plist",
    ]

    def __init__(
        self,
        service_names: Optional[List[str]] = None,
        config_file: Optional[str] = None,
        config_dir: Optional[str] = None,
    ):
        self.service_names = service_names or [self.DEFAULT_SERVICE_NAME, "ssh"]
        self.config_file = config_file or "/etc/ssh/sshd_config"
        self.config_dir = config_dir or "/etc/ssh/sshd_config.d"

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
        """Check if OpenSSH binaries (sshd / ssh) are available on macOS."""
        ssh_bin = shutil.which("ssh") or "/usr/bin/ssh"
        sshd_bin = shutil.which("sshd") or "/usr/sbin/sshd"

        has_binary = os.path.exists(ssh_bin) or os.path.exists(sshd_bin)
        if not has_binary:
            return False, None

        # Check OpenSSH version safely using ssh -V
        target_bin = ssh_bin if os.path.exists(ssh_bin) else sshd_bin
        code, stdout, stderr = self.run_safe_cmd([target_bin, "-V"])
        output = stderr or stdout or ""
        match = re.search(r"OpenSSH_([^\s,]+)", output)
        version = match.group(1) if match else "installed (OpenSSH binary found)"
        return True, version

    def discover_service_name(self) -> Tuple[str, bool]:
        """Discover the macOS launchd SSH service name and verify plist presence."""
        for path in self.LAUNCHD_PLIST_PATHS:
            if os.path.isfile(path):
                return self.DEFAULT_SERVICE_NAME, True

        # Check launchctl list
        if shutil.which("launchctl"):
            for candidate in self.service_names:
                code, stdout, stderr = self.run_safe_cmd(["launchctl", "list", candidate])
                combined = (stdout + " " + stderr).lower()
                if code == 0:
                    return candidate, True
                if "could not find service" not in combined and code != 113 and code != 1:
                    return candidate, True

        return self.DEFAULT_SERVICE_NAME, False

    def check_service_enabled(self, service_name: str) -> Tuple[StartupState, bool]:
        """Check whether the launchd SSH service is enabled (loaded in launchd)."""
        if not shutil.which("launchctl"):
            return StartupState.UNKNOWN, False

        target_service = service_name or self.DEFAULT_SERVICE_NAME
        code, stdout, stderr = self.run_safe_cmd(["launchctl", "list", target_service])
        combined = (stdout + " " + stderr).lower()

        if code == 0:
            return StartupState.ENABLED, True
        elif "could not find service" in combined or code in (1, 113):
            return StartupState.DISABLED, False
        else:
            return StartupState.UNKNOWN, False

    def check_service_status(self, service_name: str) -> Tuple[ServiceState, bool]:
        """Check whether an SSH daemon process is actively running or listening."""
        installed, _ = self.check_package_installed()
        _, service_exists = self.discover_service_name()

        # Check 1: Is sshd process running?
        is_process_running = False
        if shutil.which("pgrep"):
            code, stdout, _ = self.run_safe_cmd(["pgrep", "-x", "sshd"])
            if code == 0 and stdout:
                is_process_running = True
        elif shutil.which("ps"):
            code, stdout, _ = self.run_safe_cmd(["ps", "-ax", "-o", "comm="])
            if code == 0 and "sshd" in stdout:
                is_process_running = True

        # Check 2: Is port 22 listening?
        listening_ports = self.check_listening_ports()
        has_listening_socket = len(listening_ports) > 0

        if is_process_running or has_listening_socket:
            return ServiceState.ACTIVE, True

        if installed or service_exists:
            return ServiceState.INACTIVE, False

        return ServiceState.NOT_FOUND, False

    def check_listening_ports(self, configured_port: Optional[int] = None) -> List[SSHListeningPort]:
        """Safely determine if SSH is listening on network sockets on macOS."""
        results: List[SSHListeningPort] = []
        target_port = configured_port or 22

        # Method 1: netstat -an -p tcp (Standard BSD/macOS unprivileged tool)
        if shutil.which("netstat"):
            code, stdout, _ = self.run_safe_cmd(["netstat", "-an", "-p", "tcp"])
            if code == 0 and stdout:
                for line in stdout.splitlines():
                    if "LISTEN" not in line:
                        continue
                    parts = line.split()
                    if len(parts) >= 4:
                        proto = parts[0].lower()
                        local_endpoint = parts[3]
                        if "." in local_endpoint:
                            addr_part, port_part = local_endpoint.rsplit(".", 1)
                            if port_part == str(target_port):
                                clean_addr = addr_part
                                if clean_addr == "*":
                                    clean_addr = "::" if "6" in proto else "0.0.0.0"
                                if not any(r.port == target_port and r.address == clean_addr for r in results):
                                    results.append(
                                        SSHListeningPort(
                                            port=target_port,
                                            address=clean_addr,
                                            protocol="tcp",
                                            process="sshd" if target_port == 22 else None,
                                        )
                                    )

        # Method 2: lsof -nP -iTCP:<target_port> -sTCP:LISTEN (to enrich process name)
        if shutil.which("lsof"):
            code, stdout, _ = self.run_safe_cmd(
                ["lsof", "-nP", f"-iTCP:{target_port}", "-sTCP:LISTEN"]
            )
            if code == 0 and stdout:
                lines = stdout.splitlines()
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 9:
                        proc_name = parts[0]
                        name_col = parts[8]
                        addr = "0.0.0.0"
                        if ":" in name_col:
                            addr = name_col.split(":", 1)[0]
                            if addr == "*":
                                addr = "0.0.0.0"

                        matched = False
                        for p in results:
                            if p.port == target_port and (p.address == addr or p.address in ("0.0.0.0", "::")):
                                p.process = proc_name
                                matched = True
                                break
                        if not matched:
                            results.append(
                                SSHListeningPort(
                                    port=target_port,
                                    address=addr,
                                    protocol="tcp",
                                    process=proc_name,
                                )
                            )

        return results

    def parse_ssh_configuration(self) -> SSHConfigSummary:
        """Safely parse OpenSSH server configuration files on macOS."""
        config_files_to_read: List[str] = []

        if os.path.isfile(self.config_file):
            config_files_to_read.append(self.config_file)

        if os.path.isdir(self.config_dir):
            drop_ins = sorted(glob.glob(os.path.join(self.config_dir, "*.conf")))
            config_files_to_read.extend(drop_ins)

        summary = SSHConfigSummary(config_files_inspected=config_files_to_read)
        extracted: Dict[str, str] = {}

        for filepath in config_files_to_read:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue

                        tokens = stripped.split(None, 1)
                        if not tokens:
                            continue
                        key = tokens[0].lower()
                        val = tokens[1].strip().strip('"').strip("'") if len(tokens) > 1 else ""

                        if key not in extracted:
                            extracted[key] = val
            except (IOError, PermissionError) as e:
                logger.warning("Could not read macOS SSH config file %s: %s", filepath, e)

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
        """Aggregate macOS detection signals into a structured status report."""
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
