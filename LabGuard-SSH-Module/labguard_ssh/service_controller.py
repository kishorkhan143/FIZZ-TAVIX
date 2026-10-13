"""Privileged Service Controller for LabGuard SSH Module.

Manages systemd SSH service control and firewall allowlists with strict safety rails:
- Privileged operations isolated from detection
- Root privilege requirement checks
- Master safety switch enforcement
- Lockout risk warnings and session persistence notices
- Rule preservation (NEVER flushes or overwrites existing firewall policy)
- Dry-run planning capabilities
"""

from __future__ import annotations

import datetime
import ipaddress
import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from labguard_ssh.config import SSHModuleSettings, get_settings
from labguard_ssh.models import (
    ActionResponse,
    AllowlistPlan,
    AllowlistRuleProposal,
    DisableSSHRequest,
    AllowlistApplyRequest,
)

logger = logging.getLogger("labguard_ssh.service_controller")

LOCKOUT_WARNING = (
    "CRITICAL WARNING: Stopping SSH will prevent NEW SSH connections immediately. "
    "However, existing active SSH sessions are not automatically terminated by systemd. "
    "If you lose access or disconnect, remote administration will be unavailable without "
    "an alternative out-of-band console (e.g., physical access, IPMI, cloud serial console)."
)


class ControllerSecurityError(Exception):
    """Raised when a security guard or privilege prerequisite is violated."""
    pass


class SSHServiceController:
    """Manages privileged system modifications with safety verification."""

    def __init__(self, settings: Optional[SSHModuleSettings] = None):
        self.settings = settings or get_settings()

    def is_root(self) -> bool:
        """Check if current process has root/administrator privileges."""
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
        return False

    def run_command(self, args: List[str], timeout: float = 5.0) -> Tuple[int, str, str]:
        """Safely execute system command via argument list without shell=True."""
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
            return -1, "", "Execution timed out"
        except FileNotFoundError:
            return 127, "", f"Command binary '{args[0]}' not found"
        except Exception as e:
            return -1, "", str(e)

    def disable_ssh_service(self, request: DisableSSHRequest, service_name: str = "ssh") -> ActionResponse:
        """Stop and disable the SSH systemd service with explicit authorization.

        Never uninstalls OpenSSH.
        """
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Safety Check 1: Explicit Confirmation
        if not request.confirm:
            raise ControllerSecurityError("Operation aborted: Explicit 'confirm=true' is required.")

        # Safety Check 2: Lockout Risk Acknowledgment
        if not request.acknowledged_lockout_risk:
            raise ControllerSecurityError(
                "Operation aborted: Lockout risk must be explicitly acknowledged ('acknowledged_lockout_risk=true')."
            )

        # Safety Check 3: Master Configuration Switch
        if not self.settings.allow_privileged_operations:
            raise ControllerSecurityError(
                "Operation rejected by safety policy: LABGUARD_ALLOW_PRIVILEGED_OPERATIONS is set to False. "
                "Live system modifications are blocked."
            )

        # Safety Check 4: Elevated Privileges
        if not self.is_root():
            raise ControllerSecurityError(
                "Insufficient privileges: Administrator (root) privileges required to stop and disable systemd services."
            )

        # Safety Check 5: Windows Platform Guard
        import sys
        if sys.platform == "win32":
            raise ControllerSecurityError(
                "Windows service modification is unsupported in this module version. "
                "Stopping SSH services on Windows must be managed directly via Windows Services (services.msc)."
            )

        # Safety Check 6: Systemd availability
        if not shutil.which("systemctl"):
            raise ControllerSecurityError("systemctl binary not found on this system.")

        # Execute systemctl stop
        stop_code, stop_out, stop_err = self.run_command(["systemctl", "stop", f"{service_name}.service"])
        if stop_code != 0:
            logger.error("Failed to stop %s: %s", service_name, stop_err)
            return ActionResponse(
                success=False,
                operation="DISABLE_SSH",
                message=f"Failed to stop {service_name}.service: {stop_err or stop_out}",
                warnings=[LOCKOUT_WARNING],
                details={"stop_exit_code": stop_code, "stderr": stop_err},
                timestamp=now_ts,
            )

        # Execute systemctl disable
        disable_code, disable_out, disable_err = self.run_command(
            ["systemctl", "disable", f"{service_name}.service"]
        )
        if disable_code != 0:
            logger.warning("Service stopped but failed to disable: %s", disable_err)
            return ActionResponse(
                success=False,
                operation="DISABLE_SSH",
                message=f"Service {service_name} was stopped but could not be disabled at startup: {disable_err}",
                warnings=[LOCKOUT_WARNING],
                details={"stop_exit_code": 0, "disable_exit_code": disable_code, "stderr": disable_err},
                timestamp=now_ts,
            )

        logger.info("Successfully stopped and disabled %s.service", service_name)
        return ActionResponse(
            success=True,
            operation="DISABLE_SSH",
            message=f"SSH service ({service_name}.service) has been stopped and disabled.",
            warnings=[
                LOCKOUT_WARNING,
                "Note: Active established SSH sessions are NOT terminated automatically. "
                "Only new connection attempts are blocked."
            ],
            details={
                "service_name": service_name,
                "reason": request.reason,
                "uninstalled": False,  # OpenSSH package is deliberately retained
            },
            timestamp=now_ts,
        )

    def inspect_firewall(self) -> Tuple[str, List[str]]:
        """Safely inspect existing firewall configuration without modifying rules."""
        if shutil.which("ufw"):
            code, stdout, _ = self.run_command(["ufw", "status", "numbered"])
            if code == 0:
                lines = [line.strip() for line in stdout.splitlines() if line.strip()]
                return "ufw", lines

        if shutil.which("iptables"):
            code, stdout, _ = self.run_command(["iptables", "-S"])
            if code == 0:
                lines = [line.strip() for line in stdout.splitlines() if line.strip()]
                return "iptables", lines

        return "none", []

    def plan_allowlist(self, allowed_ips: List[str], port: int = 22) -> AllowlistPlan:
        """Create an inspection plan for restricting SSH access, preserving existing rules."""
        fw_type, existing_rules = self.inspect_firewall()
        proposals: List[AllowlistRuleProposal] = []
        warnings: List[str] = []

        if fw_type == "none":
            warnings.append(
                "Neither UFW nor iptables were detected in the system PATH. "
                "Allowlist planning cannot be applied via system firewall."
            )
            return AllowlistPlan(
                firewall_type="none",
                existing_rules_count=0,
                proposed_rules=[],
                safe_to_apply=False,
                warnings=warnings,
            )

        # Validate all IPs
        valid_ips: List[str] = []
        for ip_str in allowed_ips:
            try:
                net = ipaddress.ip_network(ip_str.strip(), strict=False)
                valid_ips.append(str(net))
            except ValueError as e:
                warnings.append(f"Invalid IP/network '{ip_str}': {e}")

        for ip_net in valid_ips:
            if fw_type == "ufw":
                cmd_spec = f"ufw allow from {ip_net} to any port {port} proto tcp comment 'LabGuard SSH Allowlist'"
            else:
                cmd_spec = f"iptables -A INPUT -p tcp -s {ip_net} --dport {port} -j ACCEPT -m comment --comment 'LabGuard SSH Allowlist'"

            proposals.append(
                AllowlistRuleProposal(
                    firewall_type=fw_type,
                    action="ALLOW",
                    rule_spec=cmd_spec,
                    ip_network=ip_net,
                    preserves_existing=True,
                )
            )

        warnings.append(
            "EXISTING RULES ARE PRESERVED. Rules are proposed as additive insertions. "
            "Firewall flush (e.g. ufw reset, iptables -F) is strictly forbidden."
        )

        return AllowlistPlan(
            firewall_type=fw_type,
            existing_rules_count=len(existing_rules),
            proposed_rules=proposals,
            safe_to_apply=len(valid_ips) > 0 and fw_type != "none",
            warnings=warnings,
        )

    def apply_allowlist(self, request: AllowlistApplyRequest, port: int = 22) -> ActionResponse:
        """Apply allowlist rules with safety verification, or perform a dry-run."""
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        plan = self.plan_allowlist(request.allowed_ips, port=port)

        # Dry-run handling
        if request.dry_run:
            return ActionResponse(
                success=True,
                operation="ALLOWLIST_DRY_RUN",
                message="Allowlist plan generated successfully in dry-run mode. No system changes executed.",
                warnings=plan.warnings,
                details={
                    "firewall_type": plan.firewall_type,
                    "existing_rules_count": plan.existing_rules_count,
                    "proposed_rules": [r.model_dump() for r in plan.proposed_rules],
                    "safe_to_apply": plan.safe_to_apply,
                },
                timestamp=now_ts,
            )

        # Safety Check 1: Confirmation
        if not request.confirm:
            raise ControllerSecurityError("Operation aborted: 'confirm=true' required.")

        # Safety Check 2: Alternative recovery verification
        if not request.recovery_method_confirmed:
            raise ControllerSecurityError(
                "Operation aborted: Administrator must explicitly confirm that an alternative recovery "
                "console/access method is available ('recovery_method_confirmed=true')."
            )

        # Safety Check 3: Master Configuration Switch
        if not self.settings.allow_privileged_operations:
            raise ControllerSecurityError(
                "Operation rejected by safety policy: LABGUARD_ALLOW_PRIVILEGED_OPERATIONS is False. "
                "Live firewall modification is disabled."
            )

        # Safety Check 4: Root privileges
        if not self.is_root():
            raise ControllerSecurityError("Root administrator privileges required to modify firewall rules.")

        # Safety Check 5: Plan validity
        if not plan.safe_to_apply or plan.firewall_type == "none":
            raise ControllerSecurityError("Cannot apply allowlist: firewall backend not found or no valid IPs provided.")

        import shlex
        applied_rules: List[str] = []
        for prop in plan.proposed_rules:
            # Parse command safely into argument list using shlex
            args = shlex.split(prop.rule_spec)
            code, stdout, stderr = self.run_command(args)
            if code != 0:
                logger.error("Failed to apply rule '%s': %s", prop.rule_spec, stderr)
                return ActionResponse(
                    success=False,
                    operation="APPLY_ALLOWLIST",
                    message=f"Failed while applying rule: {prop.rule_spec}. Error: {stderr or stdout}",
                    warnings=[
                        "Partial rules may have been applied. Existing rules were NOT deleted or flushed.",
                        LOCKOUT_WARNING,
                    ],
                    details={"applied_rules": applied_rules, "failed_rule": prop.rule_spec},
                    timestamp=now_ts,
                )
            applied_rules.append(prop.rule_spec)

        return ActionResponse(
            success=True,
            operation="APPLY_ALLOWLIST",
            message=f"Successfully applied {len(applied_rules)} allowlist firewall rule(s). Existing rules preserved.",
            warnings=[
                "Existing firewall rules were strictly preserved.",
                "Ensure target IPs match your administrative workstations to prevent future lockout.",
            ],
            details={"applied_rules": applied_rules, "firewall_type": plan.firewall_type},
            timestamp=now_ts,
        )
