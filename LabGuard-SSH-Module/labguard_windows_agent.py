"""LabGuard Windows Read-Only SSH Monitoring Agent.

Runs locally on a Windows PC to inspect OpenSSH Server (sshd) using safe PowerShell queries.
Serves structured status over Tailscale to the LabGuard Mac backend.

Key Security Properties:
- Read-only inspection only (zero modifying endpoints, never stops services or alters firewalls).
- Strict bearer token authentication required on all inspection requests.
- Binds to the Windows Tailscale IP by default (or 127.0.0.1 if Tailscale is not yet active).
- Never logs, echoes, or collects passwords, private keys, or tokens.
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import shutil
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

# Ensure parent directory is in path to import WindowsSSHDetector
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from labguard_ssh.windows_detector import WindowsSSHDetector

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [LabGuard-Windows-Agent] %(message)s",
)
logger = logging.getLogger("labguard.windows_agent")


def discover_tailscale_ip() -> Optional[str]:
    """Attempt to detect the Windows host's Tailscale IPv4 address safely."""
    # 1. Try tailscale CLI
    tailscale_bin = shutil.which("tailscale")
    if tailscale_bin:
        try:
            res = subprocess.run(
                [tailscale_bin, "ip", "-4"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2.0,
                shell=False,
                check=False,
            )
            ip = res.stdout.strip()
            if ip and ip.startswith("100."):
                return ip
        except Exception:
            pass

    # 2. Try PowerShell NetIPAddress query for Tailscale adapter
    ps_bin = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe"
    query = (
        "Get-NetIPAddress -InterfaceAlias '*Tailscale*' -AddressFamily IPv4 -ErrorAction SilentlyContinue "
        "| Select-Object -ExpandProperty IPAddress"
    )
    try:
        res = subprocess.run(
            [ps_bin, "-NoProfile", "-NonInteractive", "-Command", query],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2.0,
            shell=False,
            check=False,
        )
        for line in res.stdout.splitlines():
            ip = line.strip()
            if ip and ip.startswith("100."):
                return ip
    except Exception:
        pass

    return None


class WindowsAgentHandler(BaseHTTPRequestHandler):
    """HTTP Request handler for the read-only Windows agent."""

    server_token: str = ""
    detector: WindowsSSHDetector = WindowsSSHDetector()

    def _send_json(self, status_code: int, data: dict):
        """Send JSON response with secure headers."""
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _verify_auth(self) -> bool:
        """Validate bearer token from Authorization or X-LabGuard-Agent-Token header."""
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ", 1)[1].strip()
        elif "X-LabGuard-Agent-Token" in self.headers:
            token = self.headers["X-LabGuard-Agent-Token"].strip()

        if not token or not self.server_token:
            return False

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(token, self.server_token)

    def do_GET(self):
        """Handle read-only status and health queries."""
        clean_path = self.path.split("?")[0].rstrip("/")

        # Health endpoint (does not expose system metrics)
        if clean_path in ("/health", "/api/agent/health"):
            self._send_json(HTTPStatus.OK, {
                "status": "online",
                "role": "windows_ssh_agent",
                "platform": "windows",
            })
            return

        # Status inspection endpoint
        if clean_path in ("/api/agent/ssh/status", "/status"):
            if not self._verify_auth():
                logger.warning("Rejected unauthenticated request to %s from %s", clean_path, self.client_address[0])
                self._send_json(HTTPStatus.UNAUTHORIZED, {
                    "error": "Unauthorized: Valid Bearer token required in Authorization or X-LabGuard-Agent-Token header."
                })
                return

            try:
                # Perform safe, read-only PowerShell inspection
                pkg_installed, pkg_ver = self.detector.check_package_installed()
                svc_name, svc_exists = self.detector.discover_service_name()
                svc_state, is_active = self.detector.check_service_status(svc_name)
                start_state, is_enabled = self.detector.check_service_enabled(svc_name)
                cfg = self.detector.parse_ssh_configuration()
                ports = self.detector.check_listening_ports(configured_port=cfg.port or 22)

                # Return structured report matching LabGuard SSHStatusReport schema
                import datetime
                now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

                payload = {
                    "package_installed": pkg_installed,
                    "package_version": pkg_ver,
                    "service_exists": svc_exists,
                    "service_name": svc_name,
                    "service_active": is_active,
                    "service_state": svc_state.value if hasattr(svc_state, "value") else str(svc_state),
                    "service_enabled": is_enabled,
                    "startup_state": start_state.value if hasattr(start_state, "value") else str(start_state),
                    "listening_ports": [p.model_dump() if hasattr(p, "model_dump") else p for p in ports],
                    "config": cfg.model_dump() if hasattr(cfg, "model_dump") else cfg,
                    "timestamp": now_utc,
                }
                logger.info("Successfully served SSH status report to %s", self.client_address[0])
                self._send_json(HTTPStatus.OK, payload)
            except Exception as e:
                logger.error("Error inspecting OpenSSH status: %s", e)
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "error": "Error inspecting OpenSSH service",
                    "detail": str(e),
                })
            return

        # All other paths return 404
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})

    def do_POST(self):
        """Block all modifying POST requests; agent is strictly read-only."""
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "POST is disabled. This agent is read-only."})

    def log_message(self, format, *args):
        """Suppress default HTTP server stderr logging."""
        logger.debug("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)


def run_agent(host: Optional[str] = None, port: int = 8001, token: Optional[str] = None):
    """Start the read-only Windows SSH Monitoring Agent."""
    auth_token = token or os.environ.get("LABGUARD_AGENT_TOKEN")
    if not auth_token:
        logger.error(
            "CRITICAL: No authentication token configured! "
            "Set environment variable LABGUARD_AGENT_TOKEN or pass --token <SECRET>."
        )
        sys.exit(1)

    # Determine bind interface: prefer Tailscale IP for privacy
    tailscale_ip = discover_tailscale_ip()
    bind_ip = host
    if not bind_ip:
        if tailscale_ip:
            bind_ip = tailscale_ip
            logger.info("Detected Tailscale IP %s. Binding exclusively to Tailscale mesh.", bind_ip)
        else:
            bind_ip = "127.0.0.1"
            logger.warning(
                "Tailscale IP was not detected on this machine. "
                "Binding safely to localhost (127.0.0.1) for local testing. "
                "To bind explicitly across Tailscale, pass --host <Your-Tailscale-IP>."
            )

    WindowsAgentHandler.server_token = auth_token
    WindowsAgentHandler.detector = WindowsSSHDetector()

    server = ThreadingHTTPServer((bind_ip, port), WindowsAgentHandler)
    logger.info("LabGuard Windows SSH Agent running at http://%s:%d", bind_ip, port)
    logger.info("Read-only monitoring endpoint: http://%s:%d/api/agent/ssh/status", bind_ip, port)
    logger.info("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down Windows agent...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LabGuard Windows Read-Only SSH Monitoring Agent")
    parser.add_argument(
        "--host",
        default=os.environ.get("LABGUARD_AGENT_HOST"),
        help="IP address to bind to (defaults to detected Tailscale IP, or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LABGUARD_AGENT_PORT", "8001")),
        help="Port to listen on (default: 8001)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("LABGUARD_AGENT_TOKEN"),
        help="Bearer token for authentication (or set LABGUARD_AGENT_TOKEN env var)",
    )
    args = parser.parse_args()

    run_agent(host=args.host, port=args.port, token=args.token)
