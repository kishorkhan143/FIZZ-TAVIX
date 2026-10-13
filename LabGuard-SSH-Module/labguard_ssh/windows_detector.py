"""Windows OpenSSH Detection Engine for LabGuard SSH Module.

Provides safe, read-only inspection of OpenSSH Server on Windows systems using
non-interactive PowerShell queries and standard file inspection.
Never modifies system configuration, stops services, or exposes credentials.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from labguard_ssh.models import (
    SSHConfigSummary,
    SSHListeningPort,
    ServiceState,
    StartupState,
)

logger = logging.getLogger("labguard_ssh.windows_detector")


class WindowsSSHDetector:
    """Safe, read-only OpenSSH detector for Windows hosts using PowerShell."""

    DEFAULT_SERVICE_NAME = "sshd"

    def __init__(
        self,
        service_names: Optional[List[str]] = None,
        config_file: Optional[str] = None,
        config_dir: Optional[str] = None,
    ):
        self.service_names = service_names or [self.DEFAULT_SERVICE_NAME]
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")
        self.config_file = config_file or os.path.join(program_data, "ssh", "sshd_config")
        self.config_dir = config_dir or os.path.join(program_data, "ssh", "sshd_config.d")

    def run_safe_powershell(self, script: str, timeout: float = 3.0) -> Tuple[int, str, str]:
        """Execute a fixed PowerShell query safely with shell=False, NoProfile, and strict timeout."""
        ps_bin = (
            shutil.which("powershell.exe")
            or shutil.which("powershell")
            or shutil.which("pwsh.exe")
            or shutil.which("pwsh")
            or "powershell.exe"
        )

        args = [
            ps_bin,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ]

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
            logger.warning("PowerShell command timed out: %s", script)
            return -1, "", "PowerShell execution timed out"
        except FileNotFoundError:
            return 127, "", f"PowerShell executable not found: {ps_bin}"
        except Exception as e:
            logger.error("PowerShell execution error: %s", e)
            return -1, "", str(e)

    def run_powershell_json(self, script: str, timeout: float = 3.0) -> Tuple[int, Optional[Any], str]:
        """Execute PowerShell script and parse JSON output."""
        code, stdout, stderr = self.run_safe_powershell(script, timeout=timeout)
        if code != 0 or not stdout:
            return code, None, stderr

        try:
            parsed = json.loads(stdout)
            return code, parsed, stderr
        except json.JSONDecodeError as err:
            logger.debug("Failed to parse PowerShell JSON: %s (Output: %s)", err, stdout)
            return code, None, f"JSON parse error: {err}"

    def check_package_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if OpenSSH Server Windows Capability or binary is installed."""
        # 1. Query Windows Capability status via PowerShell
        query_cap = (
            "Get-WindowsCapability -Online -Name 'OpenSSH.Server*' -ErrorAction SilentlyContinue "
            "| Select-Object -Property State, Name | ConvertTo-Json -Compress"
        )
        code, data, _ = self.run_powershell_json(query_cap)
        if code == 0 and data:
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            if isinstance(data, dict):
                state = str(data.get("State", "")).lower()
                name = str(data.get("Name", ""))
                if state in ("installed", "1"):
                    # Check version if binary available
                    version = self._get_sshd_binary_version()
                    return True, version or "Windows Capability (OpenSSH.Server)"

        # 2. Fallback check: look for sshd.exe binary in standard Windows paths
        version = self._get_sshd_binary_version()
        if version:
            return True, version

        return False, None

    def _get_sshd_binary_version(self) -> Optional[str]:
        """Safely inspect sshd.exe -V if present."""
        sshd_bin = shutil.which("sshd.exe") or shutil.which("sshd")
        if not sshd_bin:
            sys_root = os.environ.get("SystemRoot", r"C:\Windows")
            candidate = os.path.join(sys_root, "System32", "OpenSSH", "sshd.exe")
            if os.path.isfile(candidate):
                sshd_bin = candidate

        if sshd_bin:
            try:
                res = subprocess.run(
                    [sshd_bin, "-V"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=2.0,
                    shell=False,
                    check=False,
                )
                output = res.stderr or res.stdout or ""
                match = re.search(r"OpenSSH_([^\s,]+)", output)
                if match:
                    return match.group(1)
                return "Installed (sshd.exe)"
            except Exception:
                return "Installed (sshd.exe)"
        return None

    @staticmethod
    def _sanitize_service_name(name: str) -> Optional[str]:
        """Validate and sanitize Windows service name to prevent command injection."""
        clean = (name or "").strip()
        if re.match(r"^[a-zA-Z0-9_\.-]+$", clean):
            return clean
        return None

    def discover_service_name(self) -> Tuple[str, bool]:
        """Determine whether the sshd Windows Service exists."""
        for candidate in self.service_names:
            safe_candidate = self._sanitize_service_name(candidate)
            if not safe_candidate:
                continue
            query = (
                f"Get-Service -Name '{safe_candidate}' -ErrorAction SilentlyContinue "
                "| Select-Object -Property Name | ConvertTo-Json -Compress"
            )
            code, data, _ = self.run_powershell_json(query)
            if code == 0 and data:
                if isinstance(data, dict) and data.get("Name"):
                    return str(data.get("Name")), True
                elif isinstance(data, list) and len(data) > 0:
                    return str(data[0].get("Name", safe_candidate)), True

        return self.DEFAULT_SERVICE_NAME, False

    def check_service_status(self, service_name: str) -> Tuple[ServiceState, bool]:
        """Check runtime status of the Windows SSH service."""
        safe_name = self._sanitize_service_name(service_name)
        if not safe_name:
            return ServiceState.NOT_FOUND, False

        query = (
            f"Get-Service -Name '{safe_name}' -ErrorAction SilentlyContinue "
            "| Select-Object -Property Status, Name | ConvertTo-Json -Compress"
        )
        code, data, _ = self.run_powershell_json(query)
        if code != 0 or not data:
            return ServiceState.NOT_FOUND, False

        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        if not isinstance(data, dict):
            return ServiceState.NOT_FOUND, False

        status_val = data.get("Status")
        # PowerShell Status can be string or integer enum:
        # 1=Stopped, 2=StartPending, 3=StopPending, 4=Running, 7=Paused
        status_str = str(status_val).lower() if status_val is not None else ""

        if status_str in ("running", "4"):
            return ServiceState.ACTIVE, True
        elif status_str in ("stopped", "1", "paused", "7"):
            return ServiceState.INACTIVE, False
        elif not status_str or status_val is None:
            return ServiceState.NOT_FOUND, False
        else:
            return ServiceState.UNKNOWN, False

    def check_service_enabled(self, service_name: str) -> Tuple[StartupState, bool]:
        """Check startup configuration of the Windows SSH service."""
        safe_name = self._sanitize_service_name(service_name)
        if not safe_name:
            return StartupState.NOT_FOUND, False

        query = (
            f"Get-Service -Name '{safe_name}' -ErrorAction SilentlyContinue "
            "| Select-Object -Property StartType | ConvertTo-Json -Compress"
        )
        code, data, _ = self.run_powershell_json(query)
        if code != 0 or not data:
            return StartupState.NOT_FOUND, False

        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        if not isinstance(data, dict):
            return StartupState.NOT_FOUND, False

        start_type = data.get("StartType")
        # 2=Automatic, 3=Manual, 4=Disabled
        start_str = str(start_type).lower() if start_type is not None else ""

        if start_str in ("automatic", "2"):
            return StartupState.ENABLED, True
        elif start_str in ("disabled", "4"):
            return StartupState.DISABLED, False
        elif start_str in ("manual", "3"):
            return StartupState.DISABLED, False
        else:
            return StartupState.UNKNOWN, False

    def check_listening_ports(self, configured_port: Optional[int] = None) -> List[SSHListeningPort]:
        """Check if OpenSSH is listening on Windows using Get-NetTCPConnection."""
        try:
            target_port = int(configured_port or 22)
            if not (1 <= target_port <= 65535):
                target_port = 22
        except (ValueError, TypeError):
            target_port = 22

        query = (
            f"Get-NetTCPConnection -LocalPort {target_port} -State Listen -ErrorAction SilentlyContinue "
            "| Select-Object -Property LocalAddress, LocalPort, OwningProcess | ConvertTo-Json -Compress"
        )
        code, data, _ = self.run_powershell_json(query)
        results: List[SSHListeningPort] = []

        if code == 0 and data:
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    addr = str(item.get("LocalAddress", "0.0.0.0"))
                    port = int(item.get("LocalPort", target_port))
                    pid = item.get("OwningProcess")
                    # Clean address
                    clean_addr = addr.strip("[]")
                    if clean_addr == "*":
                        clean_addr = "0.0.0.0"

                    if not any(r.port == port and r.address == clean_addr for r in results):
                        results.append(
                            SSHListeningPort(
                                port=port,
                                address=clean_addr,
                                protocol="tcp",
                                process=f"sshd (PID {pid})" if pid else "sshd",
                            )
                        )

        # Fallback to netstat -ano if Get-NetTCPConnection was not available or empty
        if not results:
            code, stdout, _ = self.run_safe_powershell(f"netstat -ano -p tcp | findstr :{target_port}")
            if code == 0 and stdout:
                for line in stdout.splitlines():
                    if "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            local_addr = parts[1]
                            pid = parts[4] if len(parts) >= 5 else None
                            if ":" in local_addr:
                                addr_part, port_str = local_addr.rsplit(":", 1)
                                try:
                                    p_num = int(port_str)
                                    if p_num == target_port:
                                        clean_addr = addr_part.strip("[]")
                                        if not any(r.port == p_num and r.address == clean_addr for r in results):
                                            results.append(
                                                SSHListeningPort(
                                                    port=p_num,
                                                    address=clean_addr,
                                                    protocol="tcp",
                                                    process=f"sshd (PID {pid})" if pid else "sshd",
                                                )
                                            )
                                except ValueError:
                                    pass

        return results

    def parse_ssh_configuration(self) -> SSHConfigSummary:
        """Safely parse OpenSSH server configuration files on Windows."""
        import glob
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
                logger.warning("Could not read Windows SSH config file %s: %s", filepath, e)

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

