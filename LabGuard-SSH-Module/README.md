# LabGuard SSH Security Monitoring & Access Control Module

A standalone, portable Python backend module designed for integration into the **LabGuard** platform. It provides non-invasive OpenSSH detection, security policy enforcement, and administrative access control on Linux hosts running `systemd`.

---

## Key Features

1. **Feature 1: SSH Detection (Read-Only & Non-Privileged)**
   - Detects if `openssh-server` is installed (via `dpkg-query` on Ubuntu/Debian with fallback to binary inspection).
   - Identifies whether the SSH systemd service unit exists (`ssh` or `sshd`).
   - Checks active status (`active`, `inactive`, `failed`, `unknown`).
   - Checks startup status (`enabled`, `disabled`, `static`, `masked`).
   - Discovers listening network sockets safely using `ss -tlnp` / `ss -tln`.
   - Inspects key SSH server configurations (`PermitRootLogin`, `PasswordAuthentication`, `PubkeyAuthentication`, `Port`, `MaxAuthTries`, `X11Forwarding`) from `/etc/ssh/sshd_config` and `/etc/ssh/sshd_config.d/*.conf`.
   - **Never exposes sensitive private keys, passwords, or credentials.**

2. **Feature 2: Security Policy Engine**
   - **`MONITOR_ONLY` (Default):** Strictly read-only monitoring. Automatically blocks any destructive or modifying operations.
   - **`DISABLE_SSH`:** Disables and stops the SSH service only when explicitly authorized with administrative credentials. Warns about remote lockout risk and session persistence. **Never uninstalls OpenSSH.**
   - **`ALLOWLIST`:** Restricts SSH access to approved IP addresses or CIDR ranges. Inspects existing firewall rules first, preserves existing rules, never flushes firewall tables, and requires confirmation that an alternative console recovery path exists. Dry-run planning is available.

3. **Feature 3: Backend API (FastAPI)**
   - Mountable `APIRouter` with prefix `/api/ssh`.
   - `GET /api/ssh/status`: OpenSSH installation, systemd service state, listening ports, and daemon configuration.
   - `GET /api/ssh/policy`: Current configured security policy and safety locks.
   - `POST /api/ssh/policy`: Updates active policy mode. **Changing policy never triggers automatic destructive actions.**
   - `POST /api/ssh/actions/disable`: Requests service shutdown with required confirmations (`confirm=true`, `acknowledged_lockout_risk=true`).
   - `POST /api/ssh/actions/allowlist`: Plans (dry-run) or applies firewall allowlist rules.
   - `GET /api/ssh/audit`: Recent structured JSON audit log records.

4. **Feature 4: Structured Audit Logging**
   - Logs timestamp (UTC ISO-8601), operation, policy, result (`SUCCESS`, `FAILED`, `REJECTED`, `DRY_RUN`), operator identity, client IP, error categories, and structured details.
   - Built-in credential redaction filter ensures secrets and tokens are never written to logs.

5. **Feature 5: Strict Security Controls**
   - All external commands executed via argument lists with `shell=False` and strict timeouts.
   - Master safety switch (`LABGUARD_ALLOW_PRIVILEGED_OPERATIONS=false` by default).
   - Localhost binding (`127.0.0.1`) by default.
   - Input validation on all IP addresses and CIDR notations using Python `ipaddress`.

---

## Architecture & Directory Structure

```
LabGuard-SSH-Module/
├── labguard_ssh/
│   ├── __init__.py               # Public API exports
│   ├── config.py                 # Pydantic Settings & environment variables
│   ├── models.py                 # Strict Pydantic models and Enums
│   ├── detector.py               # Cross-platform SSH detection coordinator
│   ├── windows_detector.py       # Modular Windows PowerShell OpenSSH detector
│   ├── remote_collector.py       # Tailscale remote agent collector with Pydantic validation
│   ├── policy_engine.py          # Policy state machine & validation engine
│   ├── service_controller.py     # Privileged systemd and firewall management (Linux)
│   ├── audit.py                  # Structured audit logging with secret redaction
│   └── api.py                    # FastAPI APIRouter and standalone app factory
├── tests/
│   ├── __init__.py
│   ├── test_detector.py          # Mocked tests for Linux package, service, and socket detection
│   ├── test_windows_detector.py  # Mocked tests for Windows capability, service, and TCP sockets
│   ├── test_windows_agent.py     # Mocked tests for Windows read-only agent HTTP server & auth
│   ├── test_remote_collector.py  # Mocked tests for remote collector timeouts, auth, and schema
│   ├── test_service_controller.py# Tests for privilege checks, dry-run, and safeguards
│   ├── test_policy_engine.py     # Policy transitions and validation tests
│   ├── test_api.py               # FastAPI test client integration tests
│   ├── test_audit.py             # Audit log serialization and redaction tests
│   └── test_integration.py       # Integration tests mounting router into existing apps
├── labguard_windows_agent.py     # Standalone read-only Windows agent for Tailscale monitoring
├── requirements.txt              # Production and testing dependencies
├── .env.example                  # Environment configuration template
├── integration_example.py        # Demo script showing how LabGuard mounts the router
└── README.md                     # Documentation and recovery guide
```

---

## Installation & Setup

### Prerequisites
- Python 3.9+ (Tested on Python 3.10, 3.11, 3.12, 3.14)
- Target host: Ubuntu Linux with `systemd` (OpenSSH server, UFW or iptables)

### Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration
Copy the configuration template:
```bash
cp .env.example .env
```
Edit `.env` as required:
```ini
# Initial security policy: MONITOR_ONLY (default), DISABLE_SSH, or ALLOWLIST
LABGUARD_SSH_POLICY=MONITOR_ONLY

# Administrator secret key required for action endpoints
LABGUARD_ADMIN_KEY=your-secure-admin-secret-key

# Master safety lock: set to true ONLY when live system changes are authorized
LABGUARD_ALLOW_PRIVILEGED_OPERATIONS=false

# Location of structured audit log file
LABGUARD_AUDIT_LOG_PATH=labguard_ssh_audit.log

# API interface and port binding
LABGUARD_API_HOST=127.0.0.1
LABGUARD_API_PORT=8000
```

---

## Automated Tests

Run the full pytest automated test suite:
```bash
pytest -v
```
All system calls (`systemctl`, `dpkg-query`, `ss`, PowerShell queries, `ufw`, `iptables`) are safely mocked. **Automated tests never execute actual SSH shutdowns or firewall modifications.**

### Running Windows-Specific Tests
To run the Windows detection tests specifically:
```bash
pytest tests/test_windows_detector.py -v
```

---

## Windows OpenSSH Support

The module includes a modular Windows detector ([`windows_detector.py`](file:///Users/mohammedashikak/LabGuard-SSH-Module/labguard_ssh/windows_detector.py)) designed for Windows hosts:
- **Capability / Binary Detection:** Uses safe, non-interactive PowerShell queries to check `Get-WindowsCapability -Online -Name 'OpenSSH.Server*'` with fallback to `sshd.exe -V`.
- **Service Monitoring:** Inspects the Windows `sshd` service using `Get-Service -Name sshd` to determine active state (`Running` vs `Stopped`) and startup type (`Automatic` vs `Disabled`/`Manual`).
- **Listening Socket Detection:** Inspects TCP port 22 listeners via `Get-NetTCPConnection -LocalPort 22 -State Listen`.
- **Configuration Parsing:** Safely parses Windows OpenSSH configuration at `%ProgramData%\ssh\sshd_config` (e.g. `C:\ProgramData\ssh\sshd_config`) without collecting private keys, host keys, or credentials.
- **Safety Rails:** Service and firewall modifications on Windows are intentionally blocked (`ControllerSecurityError`), keeping policy in `MONITOR_ONLY` mode and leaving Windows Defender Firewall rules intact.

---

## Remote Windows PC Monitoring over Tailscale

To monitor your Windows PC OpenSSH Server from a Mac-hosted LabGuard backend:

### 1. On Windows PC: Run the Read-Only Agent
The Windows agent ([`labguard_windows_agent.py`](file:///Users/mohammedashikak/LabGuard-SSH-Module/labguard_windows_agent.py)) binds to your Tailscale IP and listens on port 8001:
```powershell
$env:LABGUARD_AGENT_TOKEN="your-strong-secret-token"
python labguard_windows_agent.py --port 8001
```
*Note: If Tailscale is not yet active on the machine, it binds safely to `127.0.0.1` for local testing.*

### 2. On Mac Backend: Configure Remote URL & Token
Set the Windows agent Tailscale URL and shared bearer token:
```bash
export LABGUARD_WINDOWS_AGENT_URL="http://<windows-tailscale-ip>:8001"
export LABGUARD_WINDOWS_AGENT_TOKEN="your-strong-secret-token"
```

### 3. Query Windows SSH Status from Mac
- **Local Mac Detection:**
  ```bash
  curl http://127.0.0.1:8000/api/ssh/status
  ```
- **Remote Windows Detection:**
  ```bash
  curl http://127.0.0.1:8000/api/ssh/status?target=windows
  ```
  Returns validated `SSHStatusReport` for the Windows host including `package_installed`, `service_name: "sshd"`, `service_active: true`, and listening port `22`.

---

## How to Integrate with LabGuard

### Mounting the FastAPI Router
In your LabGuard backend application (`main.py` or `app.py`), simply import and include `get_ssh_router`:

```python
from fastapi import FastAPI
from labguard_ssh import get_ssh_router

# Your existing LabGuard application instance
app = FastAPI(title="LabGuard Core")

# Mount the SSH Security Module under /api/ssh
app.include_router(get_ssh_router())
```

### Direct Python Programmatic Usage
If you prefer to invoke detection inside background workers or periodic cron jobs without HTTP:

```python
from labguard_ssh import SSHDetector, PolicyEngine

detector = SSHDetector()
report = detector.get_full_report()

print(f"SSH Active: {report.service_active}")
print(f"PermitRootLogin: {report.config.permit_root_login}")
```

### Running the Standalone Integration Example
```bash
python integration_example.py
```
Or for direct Python output:
```bash
python integration_example.py --direct
```

---

## API Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/ssh/status` | Current SSH package, service, socket, and config state | No |
| `GET` | `/api/ssh/policy` | Current policy and safety switch status | No |
| `POST` | `/api/ssh/policy` | Update configured policy (`MONITOR_ONLY`, `DISABLE_SSH`, `ALLOWLIST`) | Yes (`X-LabGuard-Admin-Key`) |
| `POST` | `/api/ssh/actions/disable` | Stop and disable SSH service | Yes (`X-LabGuard-Admin-Key`) |
| `POST` | `/api/ssh/actions/allowlist` | Plan (dry-run) or apply firewall rules | Yes (`X-LabGuard-Admin-Key`) |
| `GET` | `/api/ssh/audit` | Retrieve structured audit events | Yes (`X-LabGuard-Admin-Key`) |

### Example: Disabling SSH Service
Request:
```http
POST /api/ssh/actions/disable
Host: 127.0.0.1:8000
X-LabGuard-Admin-Key: your-secure-admin-secret-key
Content-Type: application/json

{
  "confirm": true,
  "acknowledged_lockout_risk": true,
  "reason": "Decommissioning temporary lab session"
}
```

Response:
```json
{
  "success": true,
  "operation": "DISABLE_SSH",
  "message": "SSH service (ssh.service) has been stopped and disabled.",
  "warnings": [
    "CRITICAL WARNING: Stopping SSH will prevent NEW SSH connections immediately...",
    "Note: Active established SSH sessions are NOT terminated automatically. Only new connection attempts are blocked."
  ],
  "details": {
    "service_name": "ssh",
    "reason": "Decommissioning temporary lab session",
    "uninstalled": false
  },
  "timestamp": "2026-10-12T16:45:00.000000+00:00"
}
```

---

## Security Limitations & Session Persistence

### 1. Active SSH Sessions are NOT Automatically Terminated
- When `systemctl stop ssh` is executed, the SSH listening daemon stops accepting **new** incoming TCP connections.
- Existing connected users remain connected because their shell sessions run in independent child processes (`sshd: user@pts/X`).
- System administrators should be aware that stopping SSH isolates the server from future logins, but does not forcibly disconnect active sessions unless specifically targeted with process signals.

### 2. Remote Lockout Risk
- Disabling SSH or misconfiguring firewall rules on a remote server may permanently lock out remote administrators.
- Never execute `DISABLE_SSH` or apply an allowlist unless you have verified that an out-of-band recovery channel (such as an IPMI virtual console, AWS/GCP Serial Console, or physical access) is available.

---

## Recovery Instructions

If remote access is accidentally interrupted, use the following procedures from the out-of-band serial console:

### 1. Re-enabling and Starting SSH
Log into the server console as root and run:
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl status ssh
```
*(On CentOS/RHEL systems, replace `ssh` with `sshd`)*

### 2. Checking or Reverting Firewall Rules
If an allowlist rule prevents connection, inspect and remove the rule:

**Using UFW:**
```bash
sudo ufw status numbered
# To delete a specific rule by number:
sudo ufw delete <rule_number>
# Or temporarily permit your current IP:
sudo ufw allow from <YOUR_IP> to any port 22 proto tcp
```

**Using iptables:**
```bash
sudo iptables -L INPUT -n -v --line-numbers
# To delete rule number X:
sudo iptables -D INPUT <rule_number>
```
