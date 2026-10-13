"""Unit tests for RemoteSSHCollector (Mac to Windows agent over Tailscale)."""

import pytest
import httpx
from unittest.mock import MagicMock, patch

from labguard_ssh.models import SSHStatusReport
from labguard_ssh.remote_collector import (
    RemoteCollectorError,
    RemoteSSHCollector,
)


def test_missing_agent_url_raises_error():
    """Collector raises RemoteCollectorError when URL is not configured."""
    collector = RemoteSSHCollector(agent_url=None, agent_token="secret_token")
    with pytest.raises(RemoteCollectorError, match="Windows agent URL is not configured"):
        collector.collect_status()


def test_missing_agent_token_raises_error():
    """Collector raises RemoteCollectorError when token is not configured."""
    collector = RemoteSSHCollector(agent_url="http://100.64.0.5:8001", agent_token=None)
    with pytest.raises(RemoteCollectorError, match="Windows agent authentication token is not configured"):
        collector.collect_status()


def test_timeout_raises_clear_error_without_token():
    """Timeout exception raises clear message and never exposes secret token."""
    secret = "ultra_sensitive_secret_token_123"
    collector = RemoteSSHCollector(
        agent_url="http://100.64.0.5:8001",
        agent_token=secret,
        timeout=2.0,
    )

    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(RemoteCollectorError) as exc_info:
            collector.collect_status()
        err_msg = str(exc_info.value)
        assert "timed out after 2.0s" in err_msg
        assert secret not in err_msg


def test_connection_error_raises_clear_message():
    """Connect failure raises clear Tailscale / unreachable guidance."""
    collector = RemoteSSHCollector(
        agent_url="http://100.64.0.5:8001",
        agent_token="my_token",
    )

    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(RemoteCollectorError, match="Failed to connect to Windows agent"):
            collector.collect_status()


def test_auth_failure_raises_clear_error():
    """HTTP 401 response from Windows agent raises authentication error."""
    secret = "secret_agent_token"
    collector = RemoteSSHCollector(
        agent_url="http://100.64.0.5:8001",
        agent_token=secret,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(RemoteCollectorError) as exc_info:
            collector.collect_status()
        assert "Authentication failed" in str(exc_info.value)
        assert secret not in str(exc_info.value)


def test_successful_status_collection():
    """Valid JSON from Windows agent returns validated SSHStatusReport."""
    valid_payload = {
        "package_installed": True,
        "package_version": "9.5p1",
        "service_exists": True,
        "service_name": "sshd",
        "service_active": True,
        "service_state": "active",
        "service_enabled": True,
        "startup_state": "enabled",
        "listening_ports": [
            {"port": 22, "address": "0.0.0.0", "protocol": "tcp", "process": "sshd (PID 3320)"}
        ],
        "config": {
            "permit_root_login": "no",
            "password_authentication": "yes",
            "port": 22,
        },
        "timestamp": "2026-10-12T12:00:00Z",
    }

    collector = RemoteSSHCollector(
        agent_url="http://100.64.0.5:8001",
        agent_token="secret_token",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = valid_payload

    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        report = collector.collect_status()
        assert isinstance(report, SSHStatusReport)
        assert report.package_installed is True
        assert report.service_name == "sshd"
        assert report.service_active is True
        assert len(report.listening_ports) == 1
        assert report.listening_ports[0].port == 22

        # Verify headers sent
        call_headers = mock_get.call_args[1]["headers"]
        assert call_headers["Authorization"] == "Bearer secret_token"
        assert call_headers["X-LabGuard-Agent-Token"] == "secret_token"


def test_malformed_response_raises_validation_error():
    """Malformed payload missing required fields raises validation error."""
    collector = RemoteSSHCollector(
        agent_url="http://100.64.0.5:8001",
        agent_token="secret_token",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"invalid": "payload"}

    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(RemoteCollectorError, match="Invalid or malformed status payload"):
            collector.collect_status()
