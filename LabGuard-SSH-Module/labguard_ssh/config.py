"""Configuration module for LabGuard SSH Security Module."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from labguard_ssh.models import PolicyMode


class SSHModuleSettings(BaseSettings):
    """Configuration settings loaded from environment variables."""

    # Default policy is always MONITOR_ONLY
    ssh_policy: PolicyMode = Field(
        default=PolicyMode.MONITOR_ONLY,
        alias="LABGUARD_SSH_POLICY",
        description="Active policy mode (default: MONITOR_ONLY)"
    )

    # Admin authentication key / token
    admin_key: Optional[str] = Field(
        default=None,
        alias="LABGUARD_ADMIN_KEY",
        description="Secret key required for administrative action endpoints"
    )

    # Master hardware / live system safety switch
    allow_privileged_operations: bool = Field(
        default=False,
        alias="LABGUARD_ALLOW_PRIVILEGED_OPERATIONS",
        description="Master safety switch. Must be explicitly set to True to allow live systemd/firewall changes."
    )

    # Audit logging configuration
    audit_log_path: str = Field(
        default="labguard_ssh_audit.log",
        alias="LABGUARD_AUDIT_LOG_PATH",
        description="Path to JSON-lines audit log file"
    )

    # SSH systemd unit service names to check
    ssh_service_names: List[str] = Field(
        default=["ssh", "sshd"],
        description="Candidate systemd unit names (Ubuntu uses 'ssh', CentOS/Fedora uses 'sshd')"
    )

    # SSH configuration paths
    ssh_config_file: str = Field(
        default="/etc/ssh/sshd_config",
        alias="LABGUARD_SSH_CONFIG_FILE",
        description="Path to main sshd_config file"
    )
    ssh_config_dir: str = Field(
        default="/etc/ssh/sshd_config.d",
        alias="LABGUARD_SSH_CONFIG_DIR",
        description="Path to drop-in sshd configuration directory"
    )

    # API binding defaults to localhost for security
    api_host: str = Field(
        default="127.0.0.1",
        alias="LABGUARD_API_HOST",
        description="Interface to bind the HTTP API server to"
    )
    api_port: int = Field(
        default=8000,
        alias="LABGUARD_API_PORT",
        description="Port for the HTTP API server"
    )

    # Remote Windows Agent monitoring over Tailscale
    windows_agent_url: Optional[str] = Field(
        default=None,
        alias="LABGUARD_WINDOWS_AGENT_URL",
        description="Base URL for remote Windows agent over Tailscale (e.g. http://100.x.y.z:8001)"
    )
    windows_agent_token: Optional[str] = Field(
        default=None,
        alias="LABGUARD_WINDOWS_AGENT_TOKEN",
        description="Shared secret bearer token to authenticate with the remote Windows agent"
    )

    model_config = SettingsConfigDict(
        env_prefix="LABGUARD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache()
def get_settings() -> SSHModuleSettings:
    """Return cached settings instance."""
    return SSHModuleSettings()
