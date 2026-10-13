"""Policy Engine for LabGuard SSH Security Module.

Enforces policy boundaries, validates configuration changes, and orchestrates
safe execution while adhering strictly to default MONITOR_ONLY constraints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from labguard_ssh.audit import AuditLogger, get_audit_logger
from labguard_ssh.config import SSHModuleSettings, get_settings
from labguard_ssh.detector import SSHDetector
from labguard_ssh.models import (
    ActionResponse,
    AllowlistApplyRequest,
    AllowlistPlan,
    AuditResult,
    DisableSSHRequest,
    PolicyMode,
    PolicyStatusResponse,
    PolicyUpdateRequest,
    SSHStatusReport,
)
from labguard_ssh.service_controller import (
    ControllerSecurityError,
    SSHServiceController,
)

logger = logging.getLogger("labguard_ssh.policy_engine")


class PolicyEngine:
    """Core coordinator for SSH detection, policy management, and action execution."""

    def __init__(
        self,
        settings: Optional[SSHModuleSettings] = None,
        detector: Optional[SSHDetector] = None,
        controller: Optional[SSHServiceController] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.settings = settings or get_settings()
        self.detector = detector or SSHDetector(
            service_names=self.settings.ssh_service_names,
            config_file=self.settings.ssh_config_file,
            config_dir=self.settings.ssh_config_dir,
        )
        self.controller = controller or SSHServiceController(settings=self.settings)
        self.audit = audit_logger or get_audit_logger(log_path=self.settings.audit_log_path)

        # Runtime active policy starts strictly at settings default (MONITOR_ONLY)
        self.current_policy: PolicyMode = self.settings.ssh_policy
        self.configured_allowed_ips: List[str] = []

    def get_ssh_status(self) -> SSHStatusReport:
        """Run non-privileged, read-only SSH detection."""
        return self.detector.get_full_report()

    def get_policy_status(self) -> PolicyStatusResponse:
        """Return the current policy status and safety switches."""
        descriptions = {
            PolicyMode.MONITOR_ONLY: "Detection and monitoring only. System modifications are strictly prevented.",
            PolicyMode.DISABLE_SSH: "Allows authorized SSH service shutdown when explicitly confirmed by admin.",
            PolicyMode.ALLOWLIST: "Restricts SSH network access to approved IPs, preserving existing firewall rules.",
        }
        return PolicyStatusResponse(
            configured_policy=self.current_policy,
            allow_privileged_operations=self.settings.allow_privileged_operations,
            allowed_ips=list(self.configured_allowed_ips),
            requires_admin_auth=self.settings.admin_key is not None,
            description=descriptions.get(self.current_policy, ""),
        )

    def set_policy(
        self,
        request: PolicyUpdateRequest,
        operator: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> PolicyStatusResponse:
        """Update configured policy.

        CRITICAL SAFETY RULE: Changing configured policy must NOT automatically
        execute system actions (e.g. stopping SSH or modifying firewalls).
        """
        previous_policy = self.current_policy
        self.current_policy = request.policy

        if request.allowed_ips is not None:
            self.configured_allowed_ips = list(request.allowed_ips)

        details = {
            "previous_policy": previous_policy.value,
            "new_policy": self.current_policy.value,
            "allowed_ips": self.configured_allowed_ips,
            "automatic_actions_executed": False,
        }

        self.audit.log(
            operation="UPDATE_POLICY",
            policy=self.current_policy,
            result=AuditResult.SUCCESS,
            operator=operator,
            client_ip=client_ip,
            details=details,
        )

        logger.info(
            "Security policy updated from %s to %s (no destructive action triggered automatically)",
            previous_policy.value,
            self.current_policy.value,
        )
        return self.get_policy_status()

    def disable_ssh(
        self,
        request: DisableSSHRequest,
        operator: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> ActionResponse:
        """Execute SSH service shutdown if policy and safety preconditions allow."""
        # Policy enforcement: in MONITOR_ONLY, modifying operations are disallowed
        if self.current_policy == PolicyMode.MONITOR_ONLY:
            err_msg = (
                "Operation rejected: Current policy is MONITOR_ONLY. "
                "System modifications cannot be performed while in MONITOR_ONLY mode."
            )
            self.audit.log(
                operation="DISABLE_SSH",
                policy=self.current_policy,
                result=AuditResult.REJECTED,
                operator=operator,
                client_ip=client_ip,
                error_category="POLICY_VIOLATION",
                details={"reason": err_msg},
            )
            raise ControllerSecurityError(err_msg)

        try:
            # Discover actual service name from detector
            service_name, _ = self.detector.discover_service_name()
            response = self.controller.disable_ssh_service(request, service_name=service_name)

            self.audit.log(
                operation="DISABLE_SSH",
                policy=self.current_policy,
                result=AuditResult.SUCCESS if response.success else AuditResult.FAILED,
                operator=operator,
                client_ip=client_ip,
                details=response.details,
            )
            return response
        except ControllerSecurityError as err:
            self.audit.log(
                operation="DISABLE_SSH",
                policy=self.current_policy,
                result=AuditResult.REJECTED,
                operator=operator,
                client_ip=client_ip,
                error_category="SECURITY_VALIDATION_ERROR",
                details={"error": str(err)},
            )
            raise
        except Exception as err:
            self.audit.log(
                operation="DISABLE_SSH",
                policy=self.current_policy,
                result=AuditResult.FAILED,
                operator=operator,
                client_ip=client_ip,
                error_category="SYSTEM_ERROR",
                details={"error": str(err)},
            )
            raise

    def plan_allowlist(self, ips: Optional[List[str]] = None) -> AllowlistPlan:
        """Inspect existing firewall rules and generate proposed allowlist rules."""
        target_ips = ips if ips is not None else self.configured_allowed_ips
        cfg = self.detector.parse_ssh_configuration()
        port = cfg.port or 22
        return self.controller.plan_allowlist(target_ips, port=port)

    def apply_allowlist(
        self,
        request: AllowlistApplyRequest,
        operator: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> ActionResponse:
        """Apply allowlist rules or perform dry-run."""
        if self.current_policy == PolicyMode.MONITOR_ONLY and not request.dry_run:
            err_msg = (
                "Operation rejected: Current policy is MONITOR_ONLY. "
                "Firewall modifications are not permitted in MONITOR_ONLY mode."
            )
            self.audit.log(
                operation="APPLY_ALLOWLIST",
                policy=self.current_policy,
                result=AuditResult.REJECTED,
                operator=operator,
                client_ip=client_ip,
                error_category="POLICY_VIOLATION",
                details={"reason": err_msg},
            )
            raise ControllerSecurityError(err_msg)

        cfg = self.detector.parse_ssh_configuration()
        port = cfg.port or 22

        try:
            response = self.controller.apply_allowlist(request, port=port)
            audit_result = AuditResult.DRY_RUN if request.dry_run else (
                AuditResult.SUCCESS if response.success else AuditResult.FAILED
            )
            self.audit.log(
                operation="APPLY_ALLOWLIST" if not request.dry_run else "ALLOWLIST_DRY_RUN",
                policy=self.current_policy,
                result=audit_result,
                operator=operator,
                client_ip=client_ip,
                details=response.details,
            )
            return response
        except ControllerSecurityError as err:
            self.audit.log(
                operation="APPLY_ALLOWLIST",
                policy=self.current_policy,
                result=AuditResult.REJECTED,
                operator=operator,
                client_ip=client_ip,
                error_category="SECURITY_VALIDATION_ERROR",
                details={"error": str(err)},
            )
            raise
        except Exception as err:
            self.audit.log(
                operation="APPLY_ALLOWLIST",
                policy=self.current_policy,
                result=AuditResult.FAILED,
                operator=operator,
                client_ip=client_ip,
                error_category="SYSTEM_ERROR",
                details={"error": str(err)},
            )
            raise
