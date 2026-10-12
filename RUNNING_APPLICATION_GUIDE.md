# AuthSentinel - Running Application Guide

## 🎉 Application is LIVE!

**Status**: ✅ **FULLY OPERATIONAL**

```
Backend:   http://localhost:8000  (FastAPI)
Frontend:  http://localhost:5173  (React + Vite)
Database:  backend/authsentinel.db (SQLite)
WebSocket: ws://localhost:8000/ws (Real-time)
```

---

## 📍 QUICK LINKS

### Essential URLs
1. **Dashboard**: http://localhost:5173
2. **API Documentation**: http://localhost:8000/docs
3. **Backend Health**: http://localhost:8000/api/health
4. **Backend API**: http://localhost:8000

### What Each URL Does
| URL | Purpose |
|-----|---------|
| http://localhost:5173 | Main dashboard - View events, incidents, settings |
| http://localhost:8000/docs | Swagger UI - Test API endpoints interactively |
| http://localhost:8000/api/health | JSON health status - Backend & database status |
| http://localhost:8000/api/events | List authentication events |
| http://localhost:8000/api/alerts | List security alerts |
| http://localhost:8000/api/stats | System statistics |
| ws://localhost:8000/ws | WebSocket connection for real-time updates |

---

## 🖥️ DASHBOARD NAVIGATION

When you open http://localhost:5173, you'll see:

### Left Sidebar Menu
```
📊 MONITORING
  ├─ Overview        → System status, event counts, alerts
  ├─ Live Telemetry  → Real-time event stream
  └─ Incidents       → Security incidents list

🧪 INVENTORY
  ├─ Laboratories    → Lab environment config
  └─ Terminals       → Connected systems

🔧 TOOLS
  └─ CSV Analyzer    → Upload and analyze event data

⚙️  SYSTEM
  └─ Settings        → System configuration & health
```

### Overview Page Shows
- Total Events count
- Successful Logins count
- Failed Logins count
- Active Alerts count
- Mini charts showing trends
- Recent events list
- Active alerts list

---

## 🔍 API ENDPOINTS

### Get All Events
```bash
curl http://localhost:8000/api/events
curl http://localhost:8000/api/events?limit=50
curl http://localhost:8000/api/events?limit=50&offset=0
curl http://localhost:8000/api/events?username=alice
```

### Get All Alerts
```bash
curl http://localhost:8000/api/alerts
curl http://localhost:8000/api/alerts?limit=50
curl http://localhost:8000/api/alerts?resolved=false
```

### Get System Stats
```bash
curl http://localhost:8000/api/stats
```

Response:
```json
{
  "total_events": 0,
  "successful_logins": 0,
  "failed_logins": 0,
  "active_alerts": 0
}
```

### Get Backend Health
```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "OK",
  "backend": "ONLINE",
  "database": "ONLINE",
  "websocket_connections": 1,
  "collector_status": "DISCONNECTED",
  "uptime_seconds": 123.45
}
```

### Test WebSocket Connection
```javascript
// In browser console (F12):
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('✓ WebSocket connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};

// Send keep-alive ping
ws.send('ping');
```

---

## 📊 REAL-TIME FEATURES

### WebSocket Messages

The backend sends these message types:

**1. Connection Confirmation**
```json
{
  "type": "CONNECTED",
  "message": "AuthSentinel WebSocket active"
}
```

**2. New Event**
```json
{
  "type": "NEW_EVENT",
  "event": {
    "id": 1,
    "username": "alice",
    "source_ip": "192.168.1.100",
    "status": "SUCCESS",
    "risk_score": 10,
    "risk_level": "LOW",
    "timestamp": "2026-10-04T12:46:50Z"
  }
}
```

**3. New Alert**
```json
{
  "type": "NEW_ALERT",
  "alert": {
    "id": 1,
    "alert_type": "REPEATED_FAILURE",
    "username": "bob",
    "source_ip": "192.168.1.101",
    "risk_score": 85,
    "risk_level": "HIGH",
    "failure_count": 5,
    "triggered_at": "2026-10-04T12:46:50Z"
  }
}
```

**4. Collector Status Update**
```json
{
  "type": "COLLECTOR_STATUS",
  "status": "CONNECTED",
  "hostname": "LAPTOP-A",
  "ip": "192.168.1.50",
  "timestamp": "2026-10-04T12:46:50Z"
}
```

**5. Reset Notification**
```json
{
  "type": "RESET",
  "message": "All data cleared"
}
```

---

## 🔌 BACKEND API REFERENCE

### Base URL
```
http://localhost:8000
```

### Health & Status
```
GET /api/health              → Backend health status
GET /api/events              → List events
GET /api/alerts              → List alerts
GET /api/stats               → System statistics
```

### Event Management
```
GET /api/events?limit=100             → Get events with limit
GET /api/events?username=alice         → Filter by username
POST /api/events                       → Create event (from collector)
```

### Alert Management
```
GET /api/alerts?limit=50              → Get alerts
GET /api/alerts?resolved=false        → Get unresolved alerts
```

### WebSocket
```
WS /ws                                → WebSocket endpoint
```

### API Documentation (Interactive)
```
GET /docs                             → Swagger UI (interactive testing)
GET /redoc                            → ReDoc (alternative documentation)
GET /openapi.json                     → OpenAPI schema
```

---

## 🗄️ DATABASE INFORMATION

### Location
```
c:\Users\wwwki\OneDrive\Desktop\Working prototype\log\backend\authsentinel.db
```

### Tables
```sql
-- Authentication events
CREATE TABLE auth_events (
  id INTEGER PRIMARY KEY,
  event_id INTEGER,
  timestamp DATETIME,
  username VARCHAR(256),
  source_ip VARCHAR(64),
  source_host VARCHAR(256),
  target_computer VARCHAR(256),
  logon_type INTEGER,
  status VARCHAR(32),  -- SUCCESS or FAILURE
  risk_score FLOAT,
  risk_level VARCHAR(16),
  created_at DATETIME
);

-- Legacy alerts
CREATE TABLE alerts (
  id INTEGER PRIMARY KEY,
  alert_type VARCHAR(64),
  username VARCHAR(256),
  source_ip VARCHAR(64),
  risk_score FLOAT,
  failure_count INTEGER,
  triggered_at DATETIME,
  resolved BOOLEAN
);

-- Risk snapshots
CREATE TABLE risk_snapshots (
  id INTEGER PRIMARY KEY,
  entity_type VARCHAR(16),
  entity_id VARCHAR(256),
  risk_score FLOAT,
  computed_at DATETIME
);

-- Incidents
CREATE TABLE incidents (
  id INTEGER PRIMARY KEY,
  incident_id VARCHAR(64),  -- Deterministic hash-based ID
  entity_type VARCHAR(16),
  entity_id VARCHAR(256),
  status VARCHAR(16),  -- OPEN, COOLED, CLOSED
  opened_at DATETIME,
  cooled_at DATETIME,
  created_at DATETIME
);
```

### Querying the Database

Connect with SQLite3:
```bash
sqlite3 backend/authsentinel.db
```

Common queries:
```sql
-- Count events
SELECT COUNT(*) FROM auth_events;

-- Get recent events
SELECT * FROM auth_events ORDER BY timestamp DESC LIMIT 10;

-- Get high-risk events
SELECT * FROM auth_events WHERE risk_score > 50;

-- Count by user
SELECT username, COUNT(*) FROM auth_events GROUP BY username;

-- Count by status
SELECT status, COUNT(*) FROM auth_events GROUP BY status;

-- Get alerts
SELECT * FROM alerts ORDER BY triggered_at DESC;

-- Get open incidents
SELECT * FROM incidents WHERE status = 'OPEN';
```

---

## 🚀 LOADING SAMPLE DATA

To populate the application with test data:

### Option 1: Run Demo Script
```powershell
cd "c:\Users\wwwki\OneDrive\Desktop\Working prototype\log"
.\backend\venv\Scripts\python.exe demo.py
```

This imports:
- 5 CSV files (normal_login.csv, brute_force_fast.csv, etc.)
- 21 authentication events
- Computes risk scores
- Shows HIGH_RISK entities

### Option 2: Import Custom CSV
```powershell
# Prepare CSV file with headers:
# event_id, timestamp, username, source_ip, target_computer, status

# Use the API (once implemented):
curl -X POST http://localhost:8000/api/import/csv \
  -F "file=@myevents.csv"
```

### CSV Format Example
```csv
event_id,timestamp,username,source_ip,target_computer,status,logon_type
4625,2026-01-20 09:15:00,alice,192.168.1.100,PC-LAB-01,FAILURE,3
4624,2026-01-20 09:16:00,alice,192.168.1.100,PC-LAB-01,SUCCESS,3
4625,2026-01-20 09:20:00,bob,192.168.1.101,PC-LAB-02,FAILURE,3
```

---

## 🖥️ FRONTEND CONFIGURATION

### Environment Variables
```javascript
// frontend/src/useAuthSentinel.js
BACKEND_URL = http://100.124.189.109:8000
WS_URL = ws://100.124.189.109:8000/ws
```

### Local Development
For localhost development, these are automatically:
```
BACKEND_URL = http://localhost:8000
WS_URL = ws://localhost:8000/ws
```

### Modify Backend URL
Edit `frontend/src/useAuthSentinel.js`:
```javascript
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || `http://YOUR_IP:8000`;
const WS_URL = import.meta.env.VITE_WS_URL || `ws://YOUR_IP:8000/ws`;
```

---

## 🔧 BACKEND CONFIGURATION

### Main Configuration
File: `backend/config.py`

```python
class Settings(BaseSettings):
    host: str = "0.0.0.0"                    # Bind address
    port: int = 8000                         # Port number
    database_url: str = "sqlite+aiosqlite:///./authsentinel.db"
    brute_force_threshold: int = 5           # Failed attempts for alert
    brute_force_window_seconds: int = 120    # Time window (2 minutes)
    collector_secret: str = "authsentinel-lab-secret-2026"
```

### Risk Configuration
File: `backend/risk_config.yaml`

```yaml
# Time for signal contribution to decay to 50%
half_life_seconds: 600

# Event lookback window
lookback_seconds: 3600

# Risk thresholds
incident_threshold: 60    # Open incident if score ≥ 60
cool_threshold: 30        # Mark COOLED if score < 30

# Risk band definitions
risk_bands:
  NORMAL: [0, 29]
  WATCH: [30, 59]
  SUSPICIOUS: [60, 79]
  HIGH_RISK: [80, 100]
```

---

## 📈 MONITORING & LOGS

### Backend Logs (Terminal 1)
Shows in real-time:
```
INFO:     GET /api/events HTTP/1.1
INFO:     POST /api/events HTTP/1.1
INFO:     WebSocket connection established
[*] New event: username=alice status=SUCCESS
[!] Alert triggered: REPEATED_FAILURE
```

### Frontend Logs (Browser Console F12)
Shows:
```
[INFO] AuthSentinel WebSocket connecting to ws://localhost:8000/ws
[SUCCESS] WebSocket connected
[EVENT] Received message: {"type":"NEW_EVENT","event":{...}}
```

### Check Backend Status
```powershell
# Verify backend is running
curl http://localhost:8000/api/health

# Get specific endpoint details
curl http://localhost:8000/api/events -v

# Test API with data
curl http://localhost:8000/api/stats
```

---

## 🛑 STOPPING THE APPLICATION

### Stop Backend
In Terminal 1 (where backend is running):
```
Press Ctrl+C
```

### Stop Frontend
In Terminal 2 (where frontend is running):
```
Press Ctrl+C
or press 'q' in Vite dev server
```

### Stop Both
```powershell
# In any terminal
Get-Process -Name python | Stop-Process
Get-Process -Name node | Stop-Process
```

---

## 🔄 RESTARTING

### Restart Backend
```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Restart Frontend
```powershell
cd frontend
npm run dev
```

### Restart Both
Kill both processes and run the commands above in separate terminals.

---

## 💾 BACKUP & RECOVERY

### Backup Database
```powershell
Copy-Item backend/authsentinel.db backend/authsentinel.db.backup
```

### Restore Database
```powershell
Copy-Item backend/authsentinel.db.backup backend/authsentinel.db
```

### Reset Database
```powershell
Remove-Item backend/authsentinel.db
# Restart backend - it recreates automatically
```

### Clear All Data
```powershell
# Via API
curl -X DELETE http://localhost:8000/api/reset

# Or manually
Remove-Item backend/authsentinel.db
```

---

## 📞 SUPPORT

### When Something Goes Wrong

**Backend won't start**
```
Error: Address already in use
Solution: netstat -ano | findstr :8000
         taskkill /PID <PID> /F
```

**Frontend shows blank page**
```
Error: Cannot connect to backend
Solution: Check http://localhost:8000/api/health
         Check browser console (F12) for errors
```

**WebSocket not connecting**
```
Error: WS connection failed
Solution: 1. Verify backend running
         2. Check firewall allows port 8000
         3. Check browser console
```

**Database errors**
```
Error: Cannot open database
Solution: Delete authsentinel.db
         Restart backend (recreates automatically)
```

---

## 🎯 COMMON WORKFLOWS

### Workflow 1: View Recent Events
1. Open http://localhost:5173
2. Go to Monitoring → Live Telemetry
3. See real-time events in the list

### Workflow 2: Check System Health
1. Open http://localhost:5173
2. Go to Settings
3. View system status, uptime, connections

### Workflow 3: Test API
1. Open http://localhost:8000/docs
2. Find endpoint in Swagger UI
3. Click "Try it out"
4. Review request/response

### Workflow 4: Load Sample Data
1. Open Terminal 3
2. Run: python demo.py
3. Refresh browser (Ctrl+R)
4. See events populated

### Workflow 5: Monitor WebSocket
1. Open http://localhost:5173
2. Open browser console (F12)
3. Watch for WebSocket messages
4. See real-time updates

---

## ✨ YOU'RE ALL SET!

**All systems operational.**

- ✅ Backend running on port 8000
- ✅ Frontend running on port 5173
- ✅ Database initialized
- ✅ WebSocket active
- ✅ API ready

**Visit http://localhost:5173 to get started!**

---

*AuthSentinel v1.0.0*  
*October 4, 2026*
