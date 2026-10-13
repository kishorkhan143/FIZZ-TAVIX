"""LabGuard SSH Security Monitoring & Access Control Module.

Standalone Python backend module providing detection, policy enforcement,
and access control for OpenSSH services.
"""

from labguard_ssh.api import create_app, get_ssh_router
from labguard_ssh.audit import AuditLogger, get_audit_logger
from labguard_ssh.config import SSHModuleSettings, get_settings
from labguard_ssh.detector import SSHDetector
from labguard_ssh.macos_detector import MacOSSSHDetector
from labguard_ssh.windows_detector import WindowsSSHDetector
from labguard_ssh.models import (
    ActionResponse,
    AllowlistApplyRequest,
    AllowlistPlan,
    AllowlistRuleProposal,
    AuditLogEntry,
    AuditResult,
    DisableSSHRequest,
    PolicyMode,
    PolicyStatusResponse,
    PolicyUpdateRequest,
    SSHConfigSummary,
    SSHListeningPort,
    SSHStatusReport,
    ServiceState,
    StartupState,
)
from labguard_ssh.policy_engine import PolicyEngine
from labguard_ssh.remote_collector import (
    RemoteCollectorError,
    RemoteSSHCollector,
)
from labguard_ssh.service_controller import (
    ControllerSecurityError,
    SSHServiceController,
)

__version__ = "1.0.0"
__all__ = [
    "create_app",
    "get_ssh_router",
    "AuditLogger",
    "get_audit_logger",
    "SSHModuleSettings",
    "get_settings",
    "SSHDetector",
    "MacOSSSHDetector",
    "WindowsSSHDetector",
    "RemoteSSHCollector",
    "RemoteCollectorError",
    "PolicyEngine",
    "SSHServiceController",
    "ControllerSecurityError",
    "PolicyMode",
    "ServiceState",
    "StartupState",
    "AuditResult",
    "SSHConfigSummary",
    "SSHListeningPort",
    "SSHStatusReport",
    "PolicyStatusResponse",
    "PolicyUpdateRequest",
    "DisableSSHRequest",
    "AllowlistRuleProposal",
    "AllowlistPlan",
    "AllowlistApplyRequest",
    "ActionResponse",
    "AuditLogEntry",
]
