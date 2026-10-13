"""Data models and schemas for LabGuard SSH Security Module.

All models provide strict validation, sanitization, and serialization.
"""

from __future__ import annotations

import ipaddress
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class PolicyMode(str, Enum):
    """Supported security policy modes."""
    MONITOR_ONLY = "MONITOR_ONLY"
    DISABLE_SSH = "DISABLE_SSH"
    ALLOWLIST = "ALLOWLIST"


class ServiceState(str, Enum):
    """Systemd service run states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


class StartupState(str, Enum):
    """Systemd service enablement states."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    STATIC = "static"
    MASKED = "masked"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


class AuditResult(str, Enum):
    """Outcome status for auditable operations."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    DRY_RUN = "DRY_RUN"


class SSHConfigSummary(BaseModel):
    """Extracted non-sensitive SSH configuration summary."""
    permit_root_login: Optional[str] = Field(
        default=None,
        description="Value of PermitRootLogin (e.g. 'no', 'prohibit-password', 'yes')"
    )
    password_authentication: Optional[str] = Field(
        default=None,
        description="Value of PasswordAuthentication ('yes' or 'no')"
    )
    pubkey_authentication: Optional[str] = Field(
        default=None,
        description="Value of PubkeyAuthentication ('yes' or 'no')"
    )
    port: Optional[int] = Field(
        default=None,
        description="Primary SSH listening port from config"
    )
    x11_forwarding: Optional[str] = Field(
        default=None,
        description="Value of X11Forwarding ('yes' or 'no')"
    )
    max_auth_tries: Optional[int] = Field(
        default=None,
        description="MaxAuthTries value"
    )
    config_files_inspected: List[str] = Field(
        default_factory=list,
        description="List of config files safely parsed"
    )


class SSHListeningPort(BaseModel):
    """Details of a detected SSH listening socket."""
    port: int = Field(..., ge=1, le=65535)
    address: str = Field(..., description="Bind address (e.g., 0.0.0.0, 127.0.0.1, ::)")
    protocol: str = Field(default="tcp", description="Socket protocol")
    process: Optional[str] = Field(default=None, description="Process name or identifier if accessible")


class SSHStatusReport(BaseModel):
    """Complete structured status report for SSH on the host system."""
    package_installed: bool = Field(..., description="Whether openssh-server package is installed")
    package_version: Optional[str] = Field(default=None, description="OpenSSH package version if installed")
    service_exists: bool = Field(..., description="Whether SSH systemd service unit exists")
    service_name: str = Field(..., description="Name of the evaluated service (ssh or sshd)")
    service_active: bool = Field(..., description="True if service is currently active/running")
    service_state: ServiceState = Field(..., description="Detailed systemd active status")
    service_enabled: bool = Field(..., description="True if service starts on system boot")
    startup_state: StartupState = Field(..., description="Detailed systemd unit file enable state")
    listening_ports: List[SSHListeningPort] = Field(
        default_factory=list,
        description="List of detected network sockets listening for SSH"
    )
    config: SSHConfigSummary = Field(
        default_factory=SSHConfigSummary,
        description="Safely parsed SSH daemon configuration"
    )
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp of detection")


class PolicyStatusResponse(BaseModel):
    """Response model for current security policy configuration."""
    configured_policy: PolicyMode
    allow_privileged_operations: bool
    allowed_ips: List[str]
    requires_admin_auth: bool
    description: str


class PolicyUpdateRequest(BaseModel):
    """Request payload to change the configured security policy."""
    policy: PolicyMode = Field(..., description="Target policy mode")
    allowed_ips: Optional[List[str]] = Field(
        default=None,
        description="List of allowed IPv4/IPv6 addresses or CIDR blocks for ALLOWLIST policy"
    )

    @field_validator("allowed_ips")
    @classmethod
    def validate_allowed_ips(cls, ips: Optional[List[str]]) -> Optional[List[str]]:
        if ips is None:
            return None
        validated: List[str] = []
        for raw_ip in ips:
            trimmed = raw_ip.strip()
            if not trimmed:
                continue
            try:
                # Validates individual IP or network CIDR
                net = ipaddress.ip_network(trimmed, strict=False)
                validated.append(str(net))
            except ValueError as err:
                raise ValueError(f"Invalid IP address or CIDR network: '{trimmed}': {err}") from err
        return validated


class DisableSSHRequest(BaseModel):
    """Explicit confirmation payload for disabling the SSH service."""
    confirm: bool = Field(
        ...,
        description="Must be explicitly set to True to confirm SSH shutdown."
    )
    acknowledged_lockout_risk: bool = Field(
        ...,
        description=(
            "Must be explicitly set to True acknowledging that remote SSH access "
            "will be terminated for new connections and out-of-band console access may be required."
        )
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Optional justification recorded in the audit log."
    )


class AllowlistRuleProposal(BaseModel):
    """Individual proposed firewall rule preserving system safety."""
    firewall_type: str = Field(..., description="Firewall backend (ufw or iptables)")
    action: str = Field(..., description="Action to perform (e.g. 'ALLOW')")
    rule_spec: str = Field(..., description="Human-readable rule representation")
    ip_network: str = Field(..., description="Target network or host IP")
    preserves_existing: bool = Field(default=True, description="Whether existing rules are untouched")


class AllowlistPlan(BaseModel):
    """Pre-execution firewall inspection and proposed rule plan."""
    firewall_type: str
    existing_rules_count: int
    proposed_rules: List[AllowlistRuleProposal]
    safe_to_apply: bool
    warnings: List[str]


class AllowlistApplyRequest(BaseModel):
    """Payload to apply or dry-run network allowlist rules."""
    confirm: bool = Field(..., description="Must be True to confirm operation")
    recovery_method_confirmed: bool = Field(
        ...,
        description="Confirms that an alternative recovery console method is verified"
    )
    allowed_ips: List[str] = Field(..., min_length=1, description="IP addresses/CIDR blocks to permit")
    dry_run: bool = Field(default=True, description="When True, inspects and plans without applying")

    @field_validator("allowed_ips")
    @classmethod
    def validate_allowed_ips(cls, ips: List[str]) -> List[str]:
        if not ips:
            raise ValueError("allowed_ips cannot be empty")
        validated: List[str] = []
        for raw_ip in ips:
            trimmed = raw_ip.strip()
            try:
                net = ipaddress.ip_network(trimmed, strict=False)
                validated.append(str(net))
            except ValueError as err:
                raise ValueError(f"Invalid IP address/CIDR: '{trimmed}': {err}") from err
        return validated


class ActionResponse(BaseModel):
    """Standardized response for all privileged actions and dry-runs."""
    success: bool
    operation: str
    message: str
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class AuditLogEntry(BaseModel):
    """Structured audit log record format."""
    timestamp: str
    operation: str
    policy: PolicyMode
    result: AuditResult
    operator: Optional[str] = None
    client_ip: Optional[str] = None
    error_category: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
