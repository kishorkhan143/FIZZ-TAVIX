"""Remote SSH Status Collector for LabGuard.

Connects to a remote LabGuard agent (e.g. running on a Windows PC over Tailscale),
authenticates with a secure bearer token, enforces timeouts, and validates
the response through Pydantic's SSHStatusReport schema.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse
import httpx

from labguard_ssh.config import SSHModuleSettings, get_settings
from labguard_ssh.models import SSHStatusReport

logger = logging.getLogger("labguard_ssh.remote_collector")


class RemoteCollectorError(Exception):
    """Raised when remote agent collection fails."""
    pass


_UNSET = object()


class RemoteSSHCollector:
    """Collects OpenSSH status from a remote agent host over Tailscale or network."""

    def __init__(
        self,
        agent_url: Optional[str] = _UNSET,  # type: ignore[assignment]
        agent_token: Optional[str] = _UNSET,  # type: ignore[assignment]
        timeout: float = 5.0,
        settings: Optional[SSHModuleSettings] = None,
    ):
        cfg = settings or get_settings()
        self.agent_url = cfg.windows_agent_url if agent_url is _UNSET else agent_url
        self.agent_token = cfg.windows_agent_token if agent_token is _UNSET else agent_token
        self.timeout = timeout

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Sanitize URL to prevent logging credentials if embedded in the URL string."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or "unknown"
            port = f":{parsed.port}" if parsed.port else ""
            scheme = parsed.scheme or "http"
            return f"{scheme}://{host}{port}"
        except Exception:
            return "remote-agent"

    def collect_status(self) -> SSHStatusReport:
        """Fetch and validate SSH status from the remote Windows agent."""
        if not self.agent_url:
            raise RemoteCollectorError(
                "Windows agent URL is not configured. "
                "Set LABGUARD_WINDOWS_AGENT_URL (e.g., http://100.x.y.z:8001)."
            )

        if not self.agent_token:
            raise RemoteCollectorError(
                "Windows agent authentication token is not configured. "
                "Set LABGUARD_WINDOWS_AGENT_TOKEN."
            )

        sanitized_target = self._sanitize_url(self.agent_url)
        clean_base = self.agent_url.rstrip("/")
        endpoint = f"{clean_base}/api/agent/ssh/status"

        headers = {
            "Authorization": f"Bearer {self.agent_token}",
            "X-LabGuard-Agent-Token": self.agent_token,
            "User-Agent": "LabGuard-Backend-Collector/1.0",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, headers=headers)
        except httpx.TimeoutException:
            logger.warning("Timeout connecting to Windows agent at %s after %.1fs", sanitized_target, self.timeout)
            raise RemoteCollectorError(
                f"Connection to Windows agent at {sanitized_target} timed out after {self.timeout:.1f}s. "
                "Check that the agent is running and Tailscale connection is active."
            )
        except httpx.ConnectError as err:
            logger.warning("Connection failure to Windows agent at %s: %s", sanitized_target, err)
            raise RemoteCollectorError(
                f"Failed to connect to Windows agent at {sanitized_target}. "
                "Verify the Windows PC Tailscale IP and ensure port 8001 is listening."
            )
        except Exception as err:
            logger.error("Unexpected error contacting Windows agent: %s", err)
            raise RemoteCollectorError(f"Error reaching Windows agent at {sanitized_target}: {err}")

        # Handle HTTP status codes
        if response.status_code in (401, 403):
            raise RemoteCollectorError(
                f"Authentication failed: Windows agent at {sanitized_target} rejected the bearer token."
            )
        elif response.status_code == 404:
            raise RemoteCollectorError(
                f"Endpoint not found on Windows agent at {sanitized_target}. Expected {endpoint}."
            )
        elif response.status_code != 200:
            raise RemoteCollectorError(
                f"Windows agent at {sanitized_target} returned unexpected HTTP {response.status_code}."
            )

        # Parse and validate response with Pydantic
        try:
            data = response.json()
            return SSHStatusReport.model_validate(data)
        except Exception as validation_err:
            logger.error("Schema validation failure for Windows agent response: %s", validation_err)
            raise RemoteCollectorError(
                f"Invalid or malformed status payload received from Windows agent: {validation_err}"
            )
