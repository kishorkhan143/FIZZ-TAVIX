# AuthSentinel / TAVIX GUARD — Laptop A Package & Remote Defense

This package runs on **Laptop A**, automatically collects its local network IP and Windows Security telemetry (Event IDs 4624 & 4625), forwards events to the SOC dashboard (Laptop B), and listens for **Remote Defense Actions** dispatched by the administrator.

---

## 🛡️ Core Capabilities

1. **Automatic LAN IP Collection**:
   - Laptop A automatically determines its active network IP (via outbound socket resolution and system network interfaces).
   - Injects `laptop_ip` into heartbeat and event payloads, replacing Windows Security log empty placeholders (`-` / `127.0.0.1`) so the SOC dashboard always displays Laptop A's real IP address.

2. **High-Risk Anomaly Telemetry**:
   - Forwards interactive, network, and remote logon attempts in near-real-time (100ms polling).
   - 5 failed login attempts trigger an immediate **HIGH** risk `REPEATED_FAILURE` security alert on the SOC dashboard.

3. **Remote Defense Action Execution (3 Admin Buttons)**:
   - When an anomalous login appears on the dashboard, the admin can click one of three action buttons:
     - 🛑 **Shutdown**: Remotely issues a safe Windows system power-off (`shutdown /s /f /t 5`) after pre-acknowledging to the dashboard.
     - 🔒 **Lock Screen**: Immediately locks the Windows workstation screen using `user32.LockWorkStation`.
     - 🛡️ **Authorize**: Marks the activity as verified and benign ("no problem") without executing disruptive actions on Laptop A.
   - **NAT/Firewall-Proof Communication**: Laptop A polls the backend every 1.0s via outbound HTTP (`GET /api/collector/commands`), ensuring commands reach Laptop A even behind standard Windows Firewalls without needing inbound ports opened.

---

## 🚀 Setup & Execution Guide

### Step 1: Start Backend & Dashboard (Laptop B)
1. Open PowerShell as Administrator on Laptop B and run:
   ```cmd
   setup_firewall.bat
   ```
2. Start the FastAPI backend:
   ```cmd
   start_backend.bat
   ```
3. In `frontend/`, launch the dashboard:
   ```cmd
   npm run dev
   ```

### Step 2: Start Laptop A Package (Laptop A)
1. Copy the `laptop_a_package` folder to Laptop A.
2. Right-click `START_LAPTOP_A.bat` and select **Run as Administrator**.
3. When prompted, enter Laptop B's LAN IP (e.g., `192.168.1.15`).
4. Laptop A will:
   - Detect its LAN IP automatically.
   - Send system telemetry and heartbeat to the dashboard.
   - Start monitoring the Windows Security log.
   - Start the background command polling thread for admin defense actions.

---

## 🧪 Testing the 3 Admin Actions

### Triggering Anomalous High-Risk Login Alert
On Laptop A, run the test script:
```cmd
TEST_FAILED_LOGIN.bat
```
*(Or lock Windows with `Win + L` and enter a wrong password 5 times).*

The dashboard will immediately display:
- **Alert Type**: `REPEATED_FAILURE` (or Anomalous Logon)
- **Risk Level**: `HIGH` (Red Badge)
- **Endpoint**: `LAPTOP-A`
- **Collected IP**: `192.168.x.x` (Real LAN IP of Laptop A)
- **Action Buttons**: `🛑 Shutdown`, `🔒 Lock`, `🛡️ Authorize`

### Admin Actions on Dashboard:
1. **Click 🔒 Lock Screen**:
   - Laptop A receives the command within ~1 second.
   - Windows workstation locks immediately.
   - Dashboard status updates to `REMEDIATING` and receives execution ACK.
2. **Click 🛡️ Authorize ("No Problem")**:
   - Alert status updates to `AUTHORIZED` (Green Pill).
   - Marked resolved as benign activity.
   - No shutdown or lock command is dispatched to Laptop A.
3. **Click 🛑 Shutdown**:
   - Confirmation prompt appears to prevent accidental shutdown.
   - On confirmation, Laptop A receives the command, sends ACK to dashboard, and executes `shutdown /s /f /t 5`.

---

## 📋 Command Polling & Execution API

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/events` | `POST` | Ingests logon events with collected `laptop_ip`. |
| `/api/alerts/{id}/action` | `POST` | Admin triggers `shutdown`, `lock_screen`, or `authorize`. |
| `/api/collector/commands` | `GET` | Polled by Laptop A every 1s for pending actions. |
| `/api/collector/commands/{id}/ack` | `POST` | Laptop A reports execution status (`EXECUTED` / `FAILED`). |

---

## 🔒 Security & Privacy Notice
- AuthSentinel **never** reads, stores, or transmits user passwords.
- Only security event metadata (Event IDs 4624/4625, username, timestamp, and collected host IP) is forwarded.
