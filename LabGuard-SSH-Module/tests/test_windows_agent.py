"""Unit tests for labguard_windows_agent.py HTTP handler and authentication."""

import io
import json
import pytest
from unittest.mock import MagicMock, patch

from labguard_windows_agent import (
    WindowsAgentHandler,
    discover_tailscale_ip,
)
from labguard_ssh.models import ServiceState, StartupState


class MockSocket:
    def __init__(self, data: bytes):
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()

    def makefile(self, mode="r", *args, **kwargs):
        if "r" in mode:
            return self.rfile
        return self.wfile

    def sendall(self, data):
        self.wfile.write(data)


def run_agent_request(method: str, path: str, headers: dict = None) -> str:
    """Helper to execute WindowsAgentHandler with simulated HTTP request and return output."""
    WindowsAgentHandler.server_token = "valid_secret_agent_token"

    header_lines = [f"{method} {path} HTTP/1.1", "Host: localhost:8001"]
    if headers:
        for k, v in headers.items():
            header_lines.append(f"{k}: {v}")
    raw_req = ("\r\n".join(header_lines) + "\r\n\r\n").encode("utf-8")

    mock_sock = MockSocket(raw_req)
    WindowsAgentHandler(mock_sock, ("100.64.0.1", 54321), None)
    return mock_sock.wfile.getvalue().decode("utf-8")


def test_agent_health_endpoint_no_auth_needed():
    """Health check endpoint succeeds with HTTP 200 without requiring tokens."""
    output = run_agent_request("GET", "/health")
    assert "200 OK" in output
    assert '"status": "online"' in output


def test_agent_status_without_token_returns_401():
    """Status endpoint without token is rejected with HTTP 401."""
    output = run_agent_request("GET", "/api/agent/ssh/status")
    assert "401 Unauthorized" in output
    assert "Valid Bearer token required" in output


def test_agent_status_with_invalid_token_returns_401():
    """Status endpoint with wrong token is rejected with HTTP 401."""
    output = run_agent_request("GET", "/api/agent/ssh/status", {
        "Authorization": "Bearer wrong_token_attempt"
    })
    assert "401 Unauthorized" in output


def test_agent_status_with_valid_bearer_token_returns_200():
    """Status endpoint with valid token returns 200 and structured report."""
    with patch.object(WindowsAgentHandler.detector, "check_package_installed", return_value=(True, "OpenSSH_9.5p1")), \
         patch.object(WindowsAgentHandler.detector, "discover_service_name", return_value=("sshd", True)), \
         patch.object(WindowsAgentHandler.detector, "check_service_status", return_value=(ServiceState.ACTIVE, True)), \
         patch.object(WindowsAgentHandler.detector, "check_service_enabled", return_value=(StartupState.ENABLED, True)), \
         patch.object(WindowsAgentHandler.detector, "check_listening_ports", return_value=[]):

        output = run_agent_request("GET", "/api/agent/ssh/status", {
            "Authorization": "Bearer valid_secret_agent_token"
        })
        assert "200 OK" in output
        assert '"service_name": "sshd"' in output
        assert '"service_active": true' in output


def test_agent_blocks_post_requests():
    """Agent is read-only; POST requests are rejected with 405."""
    output = run_agent_request("POST", "/api/agent/ssh/status")
    assert "405 Method Not Allowed" in output


def test_discover_tailscale_ip():
    """Verify Tailscale IP detection parses output safely."""
    with patch("shutil.which", return_value="/usr/local/bin/tailscale"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="100.80.12.34\n")
        ip = discover_tailscale_ip()
        assert ip == "100.80.12.34"
